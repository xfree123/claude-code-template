"""PreToolUse hook cho Bash và PowerShell: chặn lệnh nguy hiểm.

Chạy được trên Windows (Git Bash / PowerShell) và Linux/macOS. Chỉ dùng thư viện chuẩn.
Exit 2 = chặn lệnh; nội dung stderr được gửi lại cho Claude.
Thêm/bớt rule: sửa danh sách RULES bên dưới, rồi chạy lại selftest.py.
"""

import json
import re
import shlex
import sys

# (regex, lý do). So khớp không phân biệt hoa thường.
RULES = [
    # --- Xóa hàng loạt ngoài project (rm -r xử lý riêng trong rm_outside_project) ---
    (
        r"remove-item\b.*-recurse.*\s('|\")?([a-z]:\\?('|\")?(\s|$)|~|\$env:userprofile|\$home|\.\.)",
        "Remove-Item -Recurse nhắm vào thư mục ngoài project",
    ),
    (
        r"remove-item\b.*\s('|\")?([a-z]:\\?('|\")?\s|~|\$env:userprofile|\$home|\.\.).*-recurse",
        "Remove-Item -Recurse nhắm vào thư mục ngoài project",
    ),
    (
        r"(^|[\s;&|])(rd|rmdir)\s+/s\b.*\s([a-z]:\\?|\.\.)(\s|$)",
        "rd /s nhắm vào ổ đĩa hoặc thư mục cha",
    ),
    (r"(^|[\s;&|])del\s+(/\w\s+)*/s\b", "del /s xóa đệ quy"),
    (r"format-volume|(^|[\s;&|])format\s+[a-z]:", "format ổ đĩa"),
    # --- Git nguy hiểm ---
    (
        r"git\s+push\b(?!.*--force-with-lease).*(\s--force\b|\s-f\b)",
        "git push --force (dùng --force-with-lease và hỏi trước)",
    ),
    (r"git\s+push\b.*\s(origin\s+)?(main|master)(\s|$)", "push thẳng lên main/master"),
    (r"git\s+reset\s+--hard", "git reset --hard làm mất thay đổi chưa commit"),
    (r"git\s+clean\s+-\w*f", "git clean -f xóa file chưa track"),
    (
        r"git\s+checkout\s+(--\s+)?\.(\s|$)|git\s+restore\s+\.(\s|$)",
        "bỏ toàn bộ thay đổi chưa commit",
    ),
    # --- Database / .NET ---
    (
        r"dotnet\s+ef\s+database\s+(update|drop)",
        "dotnet ef database update/drop tác động DB thật theo connection string",
    ),
    (r"\b(drop\s+(database|table)|truncate\s+table)\b", "lệnh SQL xóa dữ liệu"),
    # --- Publish / deploy ---
    (
        r"(npm|pnpm|yarn)\s+publish|twine\s+upload|dotnet\s+nuget\s+push|nuget(\.exe)?\s+push"
        r"|cargo\s+publish|cargo\s+yank|conan\s+upload",
        "publish package",
    ),
    # --- Rust / C++ ---
    (r"cargo\s+install\b", "cargo install cài vào ~/.cargo/bin (toàn cục) — hỏi người dùng"),
    (
        r"rustup\s+(default|self\s+uninstall|toolchain\s+(uninstall|remove))",
        "đổi/xóa toolchain Rust toàn cục",
    ),
    (
        r"cmake\s+--install\b|(^|[\s;&|])(make|ninja)\s+([^;&|]*\s)?install(\s|$)",
        "cài vào hệ thống (install prefix) — hỏi người dùng",
    ),
    (r"vcpkg(\.exe)?\s+integrate\s+install", "vcpkg integrate install đổi cấu hình toàn cục"),
    # --- Hệ thống ---
    (r"(^|[\s;&|])sudo\s", "sudo"),
    (
        r"npm\s+(i|install)\s+(-g|--global)\b|pip\s+install\b.*--break-system-packages"
        r"|dotnet\s+tool\s+install\s+(-g|--global)",
        "cài đặt toàn cục",
    ),
    (
        r"restart-computer|stop-computer|(^|[\s;&|])(shutdown|reboot|poweroff)(\s|$)",
        "tắt/khởi động lại máy",
    ),
    (
        r"set-executionpolicy|reg(\.exe)?\s+(delete|add)\s+hklm|setx\s+.*\s/m(\s|$)",
        "đổi cấu hình hệ thống Windows",
    ),
    # --- Private key ---
    (
        r"(cat|type|get-content|gc|less|more|head|tail|cp|copy|scp)\s.*"
        r"(id_rsa|id_ed25519|\.pem|\.pfx|\.p12|\.key)(\s|'|\"|$)",
        "đọc/copy private key",
    ),
]

READ_VERBS = {
    "cat",
    "type",
    "get-content",
    "gc",
    "less",
    "more",
    "head",
    "tail",
    "bat",
    "grep",
    "select-string",
    "sls",
    "cp",
    "copy",
    "copy-item",
    "scp",
    "source",
    ".",
}

OUTSIDE = re.compile(r"^(/|~|\$home|\$\{home\}|\.\.([\\/]|$)|[a-z]:([\\/]|$))", re.IGNORECASE)


def rm_outside_project(cmd: str) -> bool:
    """rm -r / cmake -E rm -r / cmake -E remove_directory với đối số là đường dẫn tuyệt đối,
    ~, $HOME, ổ đĩa, hoặc thư mục cha."""
    for segment in re.split(r"&&|\|\||[;|\n]", cmd):
        try:
            # posix=False: giữ nguyên \ của đường dẫn Windows
            tokens = shlex.split(segment, posix=False)
        except ValueError:
            tokens = segment.split()
        tokens = [t.strip("'\"") for t in tokens]
        while tokens and tokens[0] in ("sudo", "command", "builtin", "xargs"):
            tokens = tokens[1:]
        if not tokens:
            continue
        prog = re.split(r"[\\/]", tokens[0])[-1].lower().removesuffix(".exe")
        if prog == "rm":
            rest = tokens[1:]
        elif prog == "cmake" and len(tokens) >= 3 and tokens[1] == "-E":
            # cmake -E rm -r <dir> / cmake -E remove_directory <dir>
            if tokens[2] == "remove_directory":
                rest = ["-r", *tokens[3:]]
            elif tokens[2] == "rm":
                rest = tokens[3:]
            else:
                continue
        else:
            continue
        flags = [t for t in rest if t.startswith("-") and t != "--"]
        args = [t for t in rest if not t.startswith("-")]
        recursive = any(
            f in ("--recursive",) or (not f.startswith("--") and re.search("[rR]", f))
            for f in flags
        )
        if recursive and any(OUTSIDE.match(a) for a in args):
            return True
    return False


def touches_env_file(cmd: str) -> bool:
    """Lệnh đọc/copy file .env hoặc .env.* (trừ .env.example)."""
    try:
        tokens = shlex.split(cmd, posix=False)
    except ValueError:
        tokens = cmd.split()
    tokens = [t.strip("'\";()") for t in tokens]
    if not any(t.lower() in READ_VERBS for t in tokens):
        return False
    for t in tokens:
        name = re.split(r"[\\/]", t)[-1].lower()
        if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            return True
    return False


def block(reason: str) -> None:
    msg = (
        f"BLOCKED (guard.py): {reason}.\n"
        "Nếu thực sự cần, hãy dừng lại và đề nghị người dùng tự chạy lệnh này.\n"
    )
    sys.stderr.buffer.write(msg.encode("utf-8"))
    sys.exit(2)


def main() -> None:
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
    except json.JSONDecodeError:
        sys.exit(0)  # không đọc được input thì không chặn nhầm
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not cmd:
        sys.exit(0)

    for pattern, reason in RULES:
        if re.search(pattern, cmd, re.IGNORECASE):
            block(reason)
    if rm_outside_project(cmd):
        block("rm -r với đường dẫn tuyệt đối/thư mục cha (trong project dùng đường dẫn tương đối)")
    if touches_env_file(cmd):
        block("đọc/copy file .env (chỉ .env.example được phép)")
    sys.exit(0)


if __name__ == "__main__":
    main()
