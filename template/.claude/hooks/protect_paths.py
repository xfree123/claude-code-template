"""PreToolUse hook cho Edit/Write/MultiEdit: chặn sửa file nhạy cảm hoặc file sinh tự động.

Chạy được trên Windows và Linux/macOS. Chỉ dùng thư viện chuẩn.
Exit 2 = chặn; stderr được gửi lại cho Claude.
Tùy chỉnh theo project: sửa PROTECTED_FILES / PROTECTED_DIRS / PROTECTED_ROOT_DIRS bên dưới.
"""

import fnmatch
import json
import os
import sys

# Tên file (so khớp không phân biệt hoa thường, hỗ trợ wildcard) -> lý do
PROTECTED_FILES = {
    ".env": "file secrets",
    ".env.*": "file secrets",
    "*.pem": "khóa/chứng chỉ",
    "*.key": "khóa/chứng chỉ",
    "*.pfx": "khóa/chứng chỉ",
    "*.p12": "khóa/chứng chỉ",
    "secrets.json": "user secrets .NET",
    "appsettings.production.json": "cấu hình production — sửa qua quy trình deploy",
    "package-lock.json": "lockfile — để package manager tự cập nhật",
    "pnpm-lock.yaml": "lockfile — để package manager tự cập nhật",
    "yarn.lock": "lockfile — để package manager tự cập nhật",
    "poetry.lock": "lockfile — để package manager tự cập nhật",
    "uv.lock": "lockfile — để package manager tự cập nhật",
    "packages.lock.json": "lockfile — để dotnet restore tự cập nhật",
    "cargo.lock": "lockfile — để cargo tự cập nhật (cargo add/update)",
    "vcpkg-lock.json": "lockfile — để vcpkg tự cập nhật",
    "conan.lock": "lockfile — để conan tự cập nhật",
    "compile_commands.json": "sinh tự động bởi CMake",
    "cmakecache.txt": "sinh tự động bởi CMake",
}
ALLOWED_FILES = {".env.example"}

# Tên thư mục (một thành phần bất kỳ trong đường dẫn) -> lý do
PROTECTED_DIRS = {
    ".git": "thư mục git",
    ".claude/hooks": "hook bảo vệ — chỉ người dùng được sửa",
    "bin": "output build — sinh tự động",
    "obj": "output build — sinh tự động",
    "node_modules": "dependency — sinh tự động",
    ".venv": "virtualenv — sinh tự động",
    "migrations": "migration — tạo bằng dotnet ef / alembic, không sửa tay",
}

# Thư mục CHỈ tính ở gốc project (wildcard được) -> lý do.
# Để ở gốc để không chặn nhầm thư mục code trùng tên, ví dụ src/build/.
PROTECTED_ROOT_DIRS = {
    "target": "output build Rust — sinh tự động",
    "build": "output build — sinh tự động",
    "out": "output build — sinh tự động",
    "cmake-build-*": "output build CLion — sinh tự động",
    "third_party": "code vendored — cập nhật qua submodule/package manager, không sửa tay",
    "vendor": "code vendored — cập nhật qua package manager, không sửa tay",
    "vcpkg_installed": "dependency vcpkg — sinh tự động",
    ".check": "log của scripts/check.py — sinh tự động",
}


def block(rel: str, reason: str) -> None:
    msg = (
        f"BLOCKED (protect_paths.py): {rel} — {reason}.\n"
        "Hỏi người dùng nếu thực sự cần sửa file này.\n"
    )
    sys.stderr.buffer.write(msg.encode("utf-8"))
    sys.exit(2)


def main() -> None:
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
    except json.JSONDecodeError:
        sys.exit(0)
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("path") or ti.get("notebook_path")
    if not path:
        sys.exit(0)

    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    root = os.path.normcase(os.path.realpath(root))
    base_dir = data.get("cwd") or root
    full = os.path.normcase(os.path.realpath(os.path.join(base_dir, path)))

    # Ngoài project
    try:
        outside = os.path.commonpath([root, full]) != root
    except ValueError:  # Windows: khác ổ đĩa (C: vs D:)
        outside = True
    if outside:
        block(path, "nằm ngoài thư mục project")

    rel = os.path.relpath(full, root).replace("\\", "/")
    parts = rel.lower().split("/")
    name = parts[-1]

    if name not in ALLOWED_FILES:
        for pattern, reason in PROTECTED_FILES.items():
            if fnmatch.fnmatch(name, pattern):
                block(rel, reason)

    dirs = parts[:-1]
    joined = "/" + "/".join(dirs) + "/"
    for d, reason in PROTECTED_DIRS.items():
        if "/" in d:
            if f"/{d}/" in joined:
                block(rel, reason)
        elif d in dirs:
            block(rel, reason)
    if len(parts) > 1:
        for pattern, reason in PROTECTED_ROOT_DIRS.items():
            if fnmatch.fnmatch(parts[0], pattern):
                block(rel, reason)
    sys.exit(0)


if __name__ == "__main__":
    main()
