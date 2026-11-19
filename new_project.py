"""Tạo project mới, hoặc thêm harness Claude Code vào project đã có code.

Chạy trên Windows / Linux / macOS, chỉ cần Python >= 3.10 và git.

    python new_project.py <thư-mục> --stack python --desc "Mô tả"
    python new_project.py <thư-mục> --stack dotnet
    python new_project.py <thư-mục> --stack rust
    python new_project.py <thư-mục> --stack cpp
    python new_project.py <thư-mục> --stack python,cpp             # repo có nhiều stack
    python new_project.py --apply <project-có-sẵn>                  # tự nhận diện stack
    python new_project.py --update <project-đã-có-harness>          # nâng cấp hook/check.py

--apply không ghi đè file nào đã có:
  - CLAUDE.md có sẵn  -> bản mẫu lưu thành CLAUDE.harness.md để gộp tay
  - .gitignore có sẵn -> chỉ nối thêm các dòng còn thiếu

--update ghi đè các file do harness quản lý (hook, check.py, command mẫu) bằng bản mới,
gộp thêm quyền/hook mới vào settings.json; KHÔNG đụng CLAUDE.md, check.config.json, code.
Xem lại bằng `git diff` trước khi commit.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TPL = HERE / "template"
STACKS = HERE / "stacks"
# Không bao giờ copy cache/sản phẩm build từ template sang project
SKIP_DIRS = {"__pycache__", ".ruff_cache", ".mypy_cache", ".pytest_cache", "target", "build"}

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except AttributeError:
        pass


def detect_stack(target: Path) -> list[str]:
    found = []
    if any((target / f).exists() for f in ("pyproject.toml", "requirements.txt", "setup.py")):
        found.append("python")
    patterns = ("*.sln", "*.slnx", "*.csproj", "src/*.sln", "src/*/*.csproj")
    if any(any(target.glob(p)) for p in patterns):
        found.append("dotnet")
    if (target / "Cargo.toml").exists():
        found.append("rust")
    if (target / "CMakeLists.txt").exists():
        found.append("cpp")
    return found


KNOWN_STACKS = ("python", "dotnet", "rust", "cpp")


def names_for(name: str) -> dict[str, str]:
    """Các dạng tên hợp lệ cho từng ngôn ngữ, dùng để điền {{...}} và __PKG__."""
    low = name.lower()
    pkg = re.sub(r"[^a-z0-9]+", "_", low).strip("_") or "app"
    if pkg[0].isdigit():
        pkg = "app_" + pkg
    crate = re.sub(r"[^a-z0-9_-]+", "-", low).strip("-_") or "app"
    if crate[0].isdigit():
        crate = "app-" + crate
    return {"NAME": name, "PKG": pkg, "CRATE": crate, "CRATE_IDENT": crate.replace("-", "_")}


def stack_section(stacks: list[str]) -> str:
    parts = []
    for s in stacks:
        f = STACKS / f"{s}.md"
        if f.exists():
            parts.append(f.read_text(encoding="utf-8").strip())
    if not parts:
        return "## Stack\n- TODO: ngôn ngữ, framework, lệnh chạy local, lệnh test."
    return "\n\n".join(parts)


def merge_gitignore(src: Path, dst: Path) -> None:
    existing = {
        line.strip() for line in dst.read_text(encoding="utf-8", errors="replace").splitlines()
    }
    missing = [
        line
        for line in src.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#") and line.strip() not in existing
    ]
    if missing:
        with dst.open("a", encoding="utf-8") as fh:
            fh.write("\n# --- thêm bởi claude-code-template ---\n" + "\n".join(missing) + "\n")
        print(f"  ~ .gitignore: nối thêm {len(missing)} dòng")
    else:
        print("  = .gitignore: đã đủ")


def merge_settings(src: Path, dst: Path) -> None:
    """Gộp .claude/settings.json: giữ mọi thứ đã có, thêm quyền và hook của harness."""
    try:
        original_text = dst.read_text(encoding="utf-8")
        cur = json.loads(original_text)
    except (json.JSONDecodeError, UnicodeDecodeError):
        alt = dst.with_name("settings.harness.json")
        shutil.copy2(src, alt)
        print(f"  ! {dst.name} không đọc được JSON -> bản mẫu lưu vào {alt.name}, gộp tay")
        return
    tpl = json.loads(src.read_text(encoding="utf-8"))
    original = json.dumps(cur, sort_keys=True)

    added = 0
    perms = cur.setdefault("permissions", {})
    for key, rules in tpl.get("permissions", {}).items():
        lst = perms.setdefault(key, [])
        for r in rules:
            # rule đã nằm ở nhóm khác (allow/ask/deny) thì giữ quyết định cũ của người dùng
            if not any(r in perms.get(k, []) for k in ("allow", "ask", "deny")):
                lst.append(r)
                added += 1

    hooks = cur.setdefault("hooks", {})
    for event, entries in tpl.get("hooks", {}).items():
        lst = hooks.setdefault(event, [])
        existing = {json.dumps(e, sort_keys=True) for e in lst}
        for e in entries:
            if json.dumps(e, sort_keys=True) not in existing:
                lst.append(e)
                added += 1

    if json.dumps(cur, sort_keys=True) == original:
        print("  = .claude/settings.json: đã có đủ quyền và hook")
        return
    bak = dst.with_name("settings.json.bak")
    if not bak.exists():  # giữ bản gốc đầu tiên, không ghi đè khi chạy lại
        bak.write_text(original_text, encoding="utf-8")
    dst.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  ~ .claude/settings.json: gộp thêm {added} mục (bản gốc: settings.json.bak)")


def copy_template(target: Path, apply: bool) -> Path:
    """Copy template, không ghi đè. Trả về đường dẫn file CLAUDE cần điền placeholder."""
    claude_file = target / "CLAUDE.md"
    for src in sorted(TPL.rglob("*")):
        if src.is_dir() or SKIP_DIRS.intersection(src.relative_to(TPL).parts):
            continue
        rel = src.relative_to(TPL)
        dst = target / rel
        if apply and rel.as_posix() == ".gitattributes":
            # Repo cũ: đổi quy tắc xuống dòng có thể làm hàng loạt file hiện "modified"
            shutil.copy2(src, target / ".gitattributes.harness")
            print("  ! .gitattributes lưu thành .gitattributes.harness — tự quyết có áp dụng không")
            continue
        if dst.exists():
            if rel.as_posix() == "CLAUDE.md":
                claude_file = target / "CLAUDE.harness.md"
                shutil.copy2(src, claude_file)
                print(
                    "  ! CLAUDE.md đã có -> bản mẫu lưu vào CLAUDE.harness.md (gộp bằng /onboard)"
                )
            elif rel.as_posix() == ".gitignore":
                merge_gitignore(src, dst)
            elif rel.as_posix() == ".claude/settings.json":
                merge_settings(src, dst)
            else:
                print(f"  = bỏ qua (đã có): {rel.as_posix()}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  + {rel.as_posix()}")
    return claude_file


def fill_placeholders(path: Path, name: str, desc: str, stacks: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    text = (
        text.replace("{{PROJECT_NAME}}", name)
        .replace("{{PROJECT_DESC}}", desc)
        .replace("{{STACK_SECTION}}", stack_section(stacks))
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def scaffold(target: Path, stack: str, names: dict[str, str]) -> None:
    """Copy khung project từ stacks/<stack>/, điền {{NAME}} {{PKG}} {{CRATE}} {{CRATE_IDENT}}
    trong nội dung và __PKG__ trong đường dẫn. Không ghi đè file đã có."""
    src_root = STACKS / stack
    if not src_root.is_dir():
        return
    for src in sorted(src_root.rglob("*")):
        if src.is_dir() or SKIP_DIRS.intersection(src.relative_to(src_root).parts):
            continue
        rel = src.relative_to(src_root).as_posix().replace("__PKG__", names["PKG"])
        dst = target / rel
        if dst.exists():
            print(f"  = bỏ qua (đã có): {rel}")
            continue
        text = src.read_text(encoding="utf-8")
        for key, val in names.items():
            text = text.replace("{{" + key + "}}", val)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8", newline="\n")
        print(f"  + {rel}")


def git(target: Path, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(target), *args], capture_output=True).returncode == 0


# File harness sở hữu: --update được phép ghi đè
HARNESS_OWNED = (
    ".claude/hooks/guard.py",
    ".claude/hooks/protect_paths.py",
    ".claude/hooks/format.py",
    ".claude/commands/task.md",
    ".claude/commands/resume.md",
    ".claude/commands/learn.md",
    ".claude/commands/onboard.md",
    "scripts/check.py",
    "docs/runs/_template/plan.md",
    "docs/runs/_template/checks.md",
    "docs/runs/_template/progress.md",
)


def update_harness(target: Path) -> int:
    if not (target / ".claude").is_dir():
        print(f"{target} chưa có harness. Dùng --apply trước.", file=sys.stderr)
        return 1
    changed = 0
    for rel in HARNESS_OWNED:
        src, dst = TPL / rel, target / rel
        if dst.exists() and dst.read_bytes() == src.read_bytes():
            continue
        mark = "~" if dst.exists() else "+"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  {mark} {rel}")
        changed += 1
    settings = target / ".claude/settings.json"
    if settings.exists():
        merge_settings(TPL / ".claude/settings.json", settings)
    else:
        shutil.copy2(TPL / ".claude/settings.json", settings)
        print("  + .claude/settings.json")
    if (target / ".gitignore").exists():
        merge_gitignore(TPL / ".gitignore", target / ".gitignore")
    print(f"\nĐã cập nhật {changed} file. Xem lại: git diff")
    print("CLAUDE.md không bị đổi. Mục Hooks trong CLAUDE.md mẫu mới:")
    print(f"  {TPL / 'CLAUDE.md'}  (chép phần cần thiết nếu muốn)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("target")
    ap.add_argument("--apply", action="store_true", help="thêm harness vào project đã có code")
    ap.add_argument(
        "--update", action="store_true", help="nâng cấp harness cho project đã áp trước đây"
    )
    ap.add_argument(
        "--stack",
        default="",
        help="python | dotnet | rust | cpp, nhiều stack cách nhau dấu phẩy (trống = tự nhận diện)",
    )
    ap.add_argument("--desc", default="TODO: mô tả project trong 1–2 câu")
    a = ap.parse_args()

    if not TPL.is_dir():
        print(f"Không thấy thư mục template/ tại {TPL}", file=sys.stderr)
        return 1
    target = Path(a.target).expanduser().resolve()
    name = target.name
    if a.update:
        print(f"Cập nhật harness: {target}")
        return update_harness(target)

    if not a.apply and target.exists() and any(target.iterdir()):
        print(
            f"{target} đã có nội dung. Dùng --apply để thêm harness vào project có sẵn.",
            file=sys.stderr,
        )
        return 1
    if a.apply and not target.is_dir():
        print(f"{target} không tồn tại.", file=sys.stderr)
        return 1
    target.mkdir(parents=True, exist_ok=True)

    stacks = [s.strip().lower() for s in a.stack.split(",") if s.strip()] or detect_stack(target)
    stacks = ["cpp" if s in ("c++", "cxx", "cmake") else s for s in stacks]
    unknown = [s for s in stacks if s not in KNOWN_STACKS]
    if unknown:
        print(f"Stack không hỗ trợ: {', '.join(unknown)}. Chọn: {', '.join(KNOWN_STACKS)}")
        return 1
    print(
        f"{'Áp harness' if a.apply else 'Tạo project'} {target} (stack: {', '.join(stacks) or '?'})"
    )

    claude_file = copy_template(target, a.apply)
    fill_placeholders(claude_file, name, a.desc, stacks)

    if not a.apply:
        names = names_for(name)
        for stack in stacks:
            scaffold(target, stack, names)

    was_repo = (target / ".git").exists()
    if not was_repo:
        git(target, "init", "-q")
        if not a.apply:
            git(target, "add", "-A")
            ok = (
                git(
                    target,
                    "-c",
                    "user.name=dev",
                    "-c",
                    "user.email=dev@localhost",
                    "commit",
                    "-q",
                    "-m",
                    "chore: khởi tạo project từ Claude Code template",
                )
                if not git(target, "config", "user.email")
                else git(
                    target, "commit", "-q", "-m", "chore: khởi tạo project từ Claude Code template"
                )
            )
            print(
                "  git: đã init và commit lần đầu"
                if ok
                else "  git: đã init (chưa commit được, kiểm tra git config)"
            )

    print("\nBước tiếp theo:")
    print(f'  cd "{target}"')
    if a.apply:
        print("  git status                      # xem file harness vừa thêm, chưa commit")
        print("  claude")
        print(
            "  /onboard                        # Claude khảo sát code, điền CLAUDE.md, lập baseline"
        )
    else:
        if "python" in stacks:
            print(
                "  python -m venv .venv && .venv\\Scripts\\activate   (Linux: .venv/bin/activate)"
            )
            print('  python -m pip install -e ".[dev]"')
        if "dotnet" in stacks:
            print(
                "  dotnet new sln -n "
                + name
                + "   # và các project: dotnet new webapi / classlib / xunit ..."
            )
        if "rust" in stacks:
            print("  rustup component add rustfmt clippy   # nếu chưa có")
        if "cpp" in stacks:
            print("  # cần: cmake >= 3.20, compiler C++17; nên có ninja, clang-format, clang-tidy")
        print("  python scripts/check.py")
        print("  claude  ->  /task <việc cần làm>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
