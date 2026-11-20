"""PostToolUse hook cho Edit/Write/MultiEdit: tự format file vừa sửa.

Không bao giờ chặn (luôn exit 0). Thiếu formatter thì bỏ qua.
- .py           : ruff check --fix + ruff format
- .cs           : dotnet format whitespace (chế độ --folder, chỉ file vừa sửa)
- .rs           : rustfmt (edition lấy từ Cargo.toml gần nhất)
- .c/.cpp/.h…   : clang-format, CHỈ khi project có .clang-format (không áp style mặc định)
- .js/.ts/.json…: prettier trong node_modules (nếu có)
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys


def run(cmd: list[str], cwd: str) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        pass


def ruff_cmd() -> list[str] | None:
    if shutil.which("ruff"):
        return ["ruff"]
    if importlib.util.find_spec("ruff"):
        return [sys.executable, "-m", "ruff"]
    return None


def rust_edition(path: str, root: str) -> str:
    """Tìm Cargo.toml gần nhất (đi ngược lên tới root) để lấy edition."""
    d = os.path.dirname(os.path.abspath(path))
    root = os.path.abspath(root)
    while True:
        cargo = os.path.join(d, "Cargo.toml")
        if os.path.isfile(cargo):
            with open(cargo, encoding="utf-8", errors="replace") as fh:
                m = re.search(r'^\s*edition\s*=\s*"(\d{4})"', fh.read(), re.M)
            if m:
                return m.group(1)
        if d == root or os.path.dirname(d) == d:
            return "2021"
        d = os.path.dirname(d)


CPP_EXT = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".ipp")


def main() -> None:
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
    except json.JSONDecodeError:
        sys.exit(0)
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("path")
    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    if not path:
        sys.exit(0)
    full = os.path.join(data.get("cwd") or root, path)
    if not os.path.isfile(full):
        sys.exit(0)

    ext = os.path.splitext(full)[1].lower()
    if ext in (".py", ".pyi"):
        ruff = ruff_cmd()
        if ruff:
            run(ruff + ["check", "-q", "--fix", full], root)
            run(ruff + ["format", "-q", full], root)
    elif ext == ".cs":
        if shutil.which("dotnet"):
            rel = os.path.relpath(full, root)
            run(["dotnet", "format", "whitespace", root, "--folder", "--include", rel], root)
    elif ext == ".rs":
        if shutil.which("rustfmt"):
            run(["rustfmt", "--edition", rust_edition(full, root), full], root)
    elif ext in CPP_EXT:
        if shutil.which("clang-format"):
            # --fallback-style=none: không có .clang-format thì không động vào file
            run(["clang-format", "-i", "--style=file", "--fallback-style=none", full], root)
    elif ext in (".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".scss", ".html", ".yml", ".yaml"):
        for name in ("prettier.cmd", "prettier"):
            p = os.path.join(root, "node_modules", ".bin", name)
            if os.path.exists(p):
                run([p, "--write", "--log-level", "warn", full], root)
                break
    sys.exit(0)


if __name__ == "__main__":
    main()
