"""Kiểm tra toàn bộ project: lint + format + type + build + test.

Exit 0 = pass. Đây là định nghĩa "xong" của project.

    python scripts/check.py            # chạy theo cấu hình
    python scripts/check.py --all      # lint toàn bộ file, bỏ qua lint_scope
    python scripts/check.py --list     # in các bước sẽ chạy, không chạy

Cấu hình (tùy chọn): scripts/check.config.json
{
  "lint_scope": "all" | "changed",   # changed = chỉ lint/format file đã đổi so với base_ref
  "base_ref": "origin/main",         # mặc định: tự tìm origin/main, main, master
  "dotnet_target": "src/App.sln",    # khi có nhiều .sln
  "dotnet_warnaserror": false,
  "rust_deny_warnings": true,        # clippy -D warnings (repo cũ nhiều warning: false)
  "cmake_build_dir": "build",        # thư mục build C++
  "cmake_build_type": "Debug",
  "cmake_preset": "dev",             # dùng CMakePresets.json thay vì -S/-B
  "cmake_args": ["-DENABLE_ASAN=ON"],# thêm tham số configure
  "cpp_exclude": ["third_party/"],   # thư mục không format/tidy (code vendored)
  "skip": ["py-type", "cpp-tidy"],   # bỏ bước theo tên
  "steps": [ {"name": "...", "cmd": ["..."]} ],        # có -> THAY toàn bộ tự nhận diện
  "extra_steps": [ {"name": "smoke", "cmd": ["..."]} ] # chạy thêm sau tự nhận diện
}
Mã thoát: 0 pass, 1 fail, 3 không có bước nào chạy (unresolved).
"""

from __future__ import annotations

import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except AttributeError:
        pass

CONFIG: dict = {}
cfg_file = ROOT / "scripts" / "check.config.json"
if cfg_file.exists():
    CONFIG = json.loads(cfg_file.read_text(encoding="utf-8"))

ARGS = set(sys.argv[1:])
LINT_SCOPE = "all" if "--all" in ARGS else CONFIG.get("lint_scope", "all")
SKIP = set(CONFIG.get("skip", []))


# ---------------------------------------------------------------- tiện ích
def which(name: str) -> str | None:
    return shutil.which(name)


def git(*args: str) -> str:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8")
        return r.stdout.strip() if r.returncode == 0 else ""
    except OSError:
        return ""


def changed_files() -> list[str]:
    """File đã thêm/sửa so với base_ref, cộng file chưa commit và chưa track."""
    base = CONFIG.get("base_ref")
    if not base:
        for ref in ("origin/main", "origin/master", "main", "master"):
            if git("rev-parse", "--verify", "--quiet", ref):
                base = ref
                break
    files: set[str] = set()
    if base:
        mb = git("merge-base", "HEAD", base) or base
        files.update(git("diff", "--name-only", "--diff-filter=ACMR", mb).splitlines())
    files.update(git("diff", "--name-only", "--diff-filter=ACMR", "HEAD").splitlines())
    files.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    return sorted(f for f in files if f and Path(f).is_file())


def python_exe() -> str:
    """Ưu tiên Python trong .venv của project."""
    for p in (ROOT / ".venv" / "Scripts" / "python.exe", ROOT / ".venv" / "bin" / "python"):
        if p.exists():
            return str(p)
    return sys.executable


def has_module(py: str, mod: str) -> bool:
    if py == sys.executable:
        return importlib.util.find_spec(mod) is not None
    r = subprocess.run([py, "-c", f"import {mod}"], capture_output=True)
    return r.returncode == 0


# ---------------------------------------------------------------- nhận diện stack
def python_steps() -> list[dict]:
    if not any((ROOT / f).exists() for f in ("pyproject.toml", "requirements.txt", "setup.py")):
        return []
    py = python_exe()
    steps: list[dict] = []
    if LINT_SCOPE == "changed":
        targets = [f for f in changed_files() if f.endswith((".py", ".pyi"))]
        lint_note = f"{len(targets)} file đã đổi"
    else:
        targets, lint_note = ["."], "toàn bộ"
    if has_module(py, "ruff"):
        if targets:
            steps.append(
                {"name": "py-lint", "cmd": [py, "-m", "ruff", "check", *targets], "note": lint_note}
            )
            steps.append(
                {
                    "name": "py-format",
                    "cmd": [py, "-m", "ruff", "format", "--check", *targets],
                    "note": lint_note,
                }
            )
    else:
        print("  (bỏ qua py-lint/py-format: chưa cài ruff — pip install ruff)")
    if has_module(py, "mypy") and list((ROOT / "src").rglob("*.py")):
        steps.append({"name": "py-type", "cmd": [py, "-m", "mypy", "src"]})
    tests = [p for p in ROOT.rglob("test_*.py") if ".venv" not in p.parts] + [
        p for p in ROOT.rglob("*_test.py") if ".venv" not in p.parts
    ]
    if tests:
        if has_module(py, "pytest"):
            steps.append({"name": "py-test", "cmd": [py, "-m", "pytest", "-q"]})
        else:
            print("  (bỏ qua py-test: có file test nhưng chưa cài pytest)")
    return steps


def dotnet_target() -> str | None:
    if CONFIG.get("dotnet_target"):
        return CONFIG["dotnet_target"]
    for pattern in ("*.sln", "*.slnx", "*.csproj", "src/*.sln", "src/*.slnx"):
        found = sorted(glob.glob(pattern))
        if found:
            if len(found) > 1:
                print(
                    f"  (nhiều {pattern}: dùng {found[0]}; sai thì đặt dotnet_target trong config)"
                )
            return found[0]
    return None


def dotnet_steps() -> list[dict]:
    target = dotnet_target()
    if not target:
        return []
    if not which("dotnet"):
        print("  (bỏ qua .NET: không tìm thấy lệnh dotnet)")
        return []
    steps: list[dict] = []
    if LINT_SCOPE == "changed":
        cs = [f for f in changed_files() if f.endswith(".cs")]
        if cs:
            steps.append(
                {
                    "name": "dotnet-format",
                    "cmd": ["dotnet", "format", target, "--verify-no-changes", "--include", *cs],
                    "note": f"{len(cs)} file đã đổi",
                }
            )
    else:
        steps.append(
            {"name": "dotnet-format", "cmd": ["dotnet", "format", target, "--verify-no-changes"]}
        )
    build = ["dotnet", "build", target, "--nologo", "-v", "q"]
    if CONFIG.get("dotnet_warnaserror"):
        build.append("-warnaserror")
    steps.append({"name": "dotnet-build", "cmd": build})
    steps.append(
        {
            "name": "dotnet-test",
            "cmd": ["dotnet", "test", target, "--nologo", "--no-build", "-v", "q"],
        }
    )
    return steps


def node_steps() -> list[dict]:
    pkg = ROOT / "package.json"
    if not pkg.exists():
        return []
    pm = (
        "pnpm"
        if (ROOT / "pnpm-lock.yaml").exists()
        else "yarn"
        if (ROOT / "yarn.lock").exists()
        else "npm"
    )
    exe = which(pm)
    if not exe:
        return []
    scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts", {})
    return [
        {"name": f"js-{s}", "cmd": [exe, "run", s]}
        for s in ("lint", "typecheck", "test", "build")
        if s in scripts
    ]


def rust_edition() -> str:
    """Edition trong Cargo.toml (kể cả [workspace.package]); mặc định 2021."""
    m = re.search(r'^\s*edition\s*=\s*"(\d{4})"', (ROOT / "Cargo.toml").read_text("utf-8"), re.M)
    return m.group(1) if m else "2021"


def rust_steps() -> list[dict]:
    if not (ROOT / "Cargo.toml").exists():
        return []
    if not which("cargo"):
        print("  (bỏ qua Rust: không tìm thấy cargo — cài qua https://rustup.rs)")
        return []
    steps: list[dict] = []
    if which("rustfmt"):
        if LINT_SCOPE == "changed":
            rs = [f for f in changed_files() if f.endswith(".rs")]
            if rs:
                steps.append(
                    {
                        "name": "rust-fmt",
                        "cmd": ["rustfmt", "--check", "--edition", rust_edition(), *rs],
                        "note": f"{len(rs)} file đã đổi",
                    }
                )
        else:
            steps.append({"name": "rust-fmt", "cmd": ["cargo", "fmt", "--all", "--", "--check"]})
    else:
        print("  (bỏ qua rust-fmt: rustup component add rustfmt)")
    if which("cargo-clippy"):
        clippy = ["cargo", "clippy", "--workspace", "--all-targets", "--quiet"]
        if CONFIG.get("rust_deny_warnings", True):
            clippy += ["--", "-D", "warnings"]
        steps.append({"name": "rust-clippy", "cmd": clippy})
    else:
        print("  (bỏ qua rust-clippy: rustup component add clippy)")
        steps.append({"name": "rust-build", "cmd": ["cargo", "build", "--workspace", "--quiet"]})
    steps.append({"name": "rust-test", "cmd": ["cargo", "test", "--workspace", "--quiet"]})
    return steps


CPP_EXT = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".ipp")
CPP_SRC_EXT = (".c", ".cc", ".cpp", ".cxx")


def cpp_build_dir() -> Path:
    return ROOT / CONFIG.get("cmake_build_dir", "build")


def cpp_excluded(rel: str) -> bool:
    rel = rel.replace("\\", "/")
    build = CONFIG.get("cmake_build_dir", "build").rstrip("/") + "/"
    prefixes = [build, "cmake-build-", "out/", *CONFIG.get("cpp_exclude", ["third_party/"])]
    return any(rel.startswith(p) for p in prefixes)


def cpp_files(ext: tuple[str, ...]) -> list[str]:
    if LINT_SCOPE == "changed":
        files = changed_files()
    else:
        files = git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()
        if not files:  # chưa phải git repo
            files = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file()]
    return sorted(f for f in files if f.lower().endswith(ext) and not cpp_excluded(f))


def cpp_tidy_cmd() -> list[str] | None:
    """Quyết định lúc chạy (sau configure) vì cần compile_commands.json."""
    db = cpp_build_dir() / "compile_commands.json"
    if not db.exists():
        print("    (không có compile_commands.json: generator Visual Studio không sinh file này.")
        print('     Dùng Ninja, hoặc đặt "skip": ["cpp-tidy"] trong check.config.json)')
        return None
    in_db = set()
    for entry in json.loads(db.read_text(encoding="utf-8")):
        p = Path(entry["directory"], entry["file"]).resolve()
        try:
            in_db.add(p.relative_to(ROOT).as_posix())
        except ValueError:
            continue  # file ngoài project (thư viện FetchContent...)
    files = [f for f in cpp_files(CPP_SRC_EXT) if f in in_db]
    if not files:
        print("    (không có file .cpp nào cần kiểm tra)")
        return None
    return ["clang-tidy", "-p", str(cpp_build_dir()), "--quiet", *files]


def cpp_steps() -> list[dict]:
    if not (ROOT / "CMakeLists.txt").exists():
        return []
    if not which("cmake"):
        print("  (bỏ qua C++: không tìm thấy cmake)")
        return []
    bdir = str(cpp_build_dir())
    btype = CONFIG.get("cmake_build_type", "Debug")
    preset = CONFIG.get("cmake_preset")
    steps: list[dict] = []

    if preset:
        configure = ["cmake", "--preset", preset]
        build = ["cmake", "--build", "--preset", preset]
        test = {"name": "cpp-test", "cmd": ["ctest", "--preset", preset, "--output-on-failure"]}
    else:
        configure = ["cmake", "-S", ".", "-B", bdir, f"-DCMAKE_BUILD_TYPE={btype}"]
        configure.append("-DCMAKE_EXPORT_COMPILE_COMMANDS=ON")
        # Chỉ chọn generator khi chưa configure, tránh lỗi "generator does not match"
        if which("ninja") and not (cpp_build_dir() / "CMakeCache.txt").exists():
            configure += ["-G", "Ninja"]
        build = ["cmake", "--build", bdir, "--config", btype, "--parallel"]
        test = {
            "name": "cpp-test",
            "cmd": ["ctest", "-C", btype, "--output-on-failure"],
            "cwd": bdir,
        }
    configure += CONFIG.get("cmake_args", [])

    steps.append({"name": "cpp-configure", "cmd": configure, "gate": True})
    if (ROOT / ".clang-format").exists():
        if which("clang-format"):
            files = cpp_files(CPP_EXT)
            if files:
                note = f"{len(files)} file" + (" đã đổi" if LINT_SCOPE == "changed" else "")
                cmd = ["clang-format", "--dry-run", "--Werror", *files]
                steps.append({"name": "cpp-format", "cmd": cmd, "note": note})
        else:
            print("  (bỏ qua cpp-format: có .clang-format nhưng chưa cài clang-format)")
    steps.append({"name": "cpp-build", "cmd": build, "gate": True})
    if (ROOT / ".clang-tidy").exists():
        if which("clang-tidy"):
            steps.append({"name": "cpp-tidy", "lazy": cpp_tidy_cmd})
        else:
            print("  (bỏ qua cpp-tidy: có .clang-tidy nhưng chưa cài clang-tidy)")
    steps.append(test)
    return steps


def go_steps() -> list[dict]:
    if not (ROOT / "go.mod").exists() or not which("go"):
        return []
    return [
        {"name": "go-vet", "cmd": ["go", "vet", "./..."]},
        {"name": "go-test", "cmd": ["go", "test", "./..."]},
    ]


# ---------------------------------------------------------------- chạy
def main() -> int:
    if "steps" in CONFIG:
        steps = list(CONFIG["steps"])
    else:
        steps = (
            python_steps() + dotnet_steps() + rust_steps() + cpp_steps() + node_steps() + go_steps()
        )
    steps += CONFIG.get("extra_steps", [])
    steps = [s for s in steps if s["name"] not in SKIP]

    print(f"check.py — lint_scope={LINT_SCOPE}")
    if "--list" in ARGS:
        for s in steps:
            if "lazy" in s:
                cmd = "(xác định lúc chạy)"
            else:
                cmd = s["cmd"] if isinstance(s["cmd"], str) else " ".join(s["cmd"])
            print(f"  {s['name']}: {cmd}")
        return 0

    failed: list[str] = []
    blocked: set[str] = set()  # stack đã fail ở bước gate (configure/build)
    ran = 0
    for s in steps:
        note = f" ({s['note']})" if s.get("note") else ""
        print(f"\n==> {s['name']}{note}", flush=True)
        stack = s["name"].split("-", 1)[0]
        if stack in blocked:
            print(f"    SKIP {s['name']} (bước configure/build trước đó fail)")
            continue
        if "lazy" in s:
            cmd = s["lazy"]()
            if cmd is None:
                print(f"    SKIP {s['name']}")
                continue
        else:
            cmd = s["cmd"]
        ran += 1
        try:
            rc = subprocess.run(
                cmd, shell=isinstance(cmd, str), cwd=s.get("cwd") or ROOT
            ).returncode
        except OSError as e:
            print(f"    lỗi chạy lệnh: {e}")
            rc = 1
        print(f"    {'PASS' if rc == 0 else 'FAIL'} {s['name']}", flush=True)
        if rc != 0:
            failed.append(s["name"])
            if s.get("gate"):
                blocked.add(stack)

    print()
    if not ran and not failed:
        print(
            "CHECK: UNRESOLVED — không có bước kiểm tra nào. Cài công cụ hoặc khai báo steps "
            "trong scripts/check.config.json."
        )
        return 3
    if failed:
        print(f"CHECK: FAIL ({len(failed)}/{ran}): {', '.join(failed)}")
        return 1
    print(f"CHECK: PASS ({ran} bước)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
