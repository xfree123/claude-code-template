"""Tự kiểm tra các hook trên máy của bạn (Windows / Linux / macOS).

    python selftest.py

Chạy guard.py và protect_paths.py với các lệnh mẫu, so với kết quả mong đợi.
Exit 0 = mọi trường hợp đúng.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent / "template" / ".claude" / "hooks"
ROOT = str(HOOKS.parent.parent)

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except AttributeError:
        pass

GUARD = [
    # (mong đợi, lệnh)
    ("BLOCK", "rm -rf /"),
    ("BLOCK", "rm -rf ~/projects"),
    ("BLOCK", "cd x && rm -r -f ../"),
    ("BLOCK", "rm -rf /c/Users"),
    ("BLOCK", r"rm -rf C:\Users\x"),
    ("BLOCK", "rm --recursive /var"),
    ("ALLOW", "rm -rf build/ && cd /tmp"),
    ("ALLOW", "rm -rf ./bin ./obj"),
    ("ALLOW", "rm -f /tmp/x.log"),
    ("BLOCK", "Remove-Item -Recurse -Force C:\\"),
    ("BLOCK", "Remove-Item C:\\ -Recurse"),
    ("BLOCK", r"Remove-Item -Recurse $env:USERPROFILE\docs"),
    ("ALLOW", r"Remove-Item -Recurse -Force .\bin"),
    ("BLOCK", "rd /s /q C:\\"),
    ("BLOCK", "del /s /q *.*"),
    ("BLOCK", "git push --force origin feat"),
    ("BLOCK", "git push -f"),
    ("ALLOW", "git push --force-with-lease origin feat"),
    ("BLOCK", "git push origin main"),
    ("ALLOW", "git push origin feature/maintenance"),
    ("BLOCK", "git reset --hard"),
    ("BLOCK", "git checkout -- ."),
    ("ALLOW", "git checkout -b fix/x"),
    ("BLOCK", "cat .env"),
    ("BLOCK", "Get-Content .env.production"),
    ("BLOCK", r"type config\.env"),
    ("ALLOW", "cat .env.example"),
    ("BLOCK", "cat .env.example .env"),
    ("ALLOW", "grep -r TODO src"),
    ("BLOCK", "dotnet ef database update"),
    ("ALLOW", "dotnet ef migrations add AddOrder"),
    ("ALLOW", "dotnet build"),
    ("BLOCK", "dotnet nuget push x.nupkg"),
    ("BLOCK", "sudo apt install x"),
    ("BLOCK", "Set-ExecutionPolicy Unrestricted"),
    ("BLOCK", "Restart-Computer"),
    ("ALLOW", "python -m pytest -q"),
    ("ALLOW", "python scripts/check.py"),
    ("ALLOW", "python scripts/check.py --failed"),
    # Rust
    ("ALLOW", "cargo build --workspace"),
    ("ALLOW", "cargo test"),
    ("ALLOW", "cargo clippy --all-targets -- -D warnings"),
    ("ALLOW", "cargo add serde"),
    ("BLOCK", "cargo publish"),
    ("BLOCK", "cargo install ripgrep"),
    ("BLOCK", "rustup default nightly"),
    ("ALLOW", "rustup component add clippy"),
    # C++
    ("ALLOW", "cmake -S . -B build -G Ninja"),
    ("ALLOW", "cmake --build build --parallel"),
    ("ALLOW", "ctest --output-on-failure"),
    ("BLOCK", "cmake --install build"),
    ("BLOCK", "sudo make install"),
    ("BLOCK", "cd build && ninja install"),
    ("ALLOW", "make -j8"),
    ("ALLOW", "cmake -E rm -rf build"),
    ("BLOCK", "cmake -E rm -rf /usr/local/include"),
    ("BLOCK", "cmake -E remove_directory ../other"),
    ("BLOCK", "vcpkg integrate install"),
]

PATHS = [
    ("BLOCK", ".env"),
    ("ALLOW", ".env.example"),
    ("BLOCK", "src/Api/appsettings.Production.json"),
    ("ALLOW", "src/Api/appsettings.json"),
    ("BLOCK", "src/Api/bin/Debug/x.dll"),
    ("BLOCK", "src/Data/Migrations/20240101_Init.cs"),
    ("BLOCK", "../other/x.py"),
    ("BLOCK", ".claude/hooks/guard.py"),
    ("ALLOW", ".claude/commands/task.md"),
    ("ALLOW", "src/app.py"),
    ("ALLOW", "src/Api/Controllers/OrderController.cs"),
    ("BLOCK", "package-lock.json"),
    ("BLOCK", "/etc/hosts" if os.name != "nt" else r"C:\Windows\System32\drivers\etc\hosts"),
    # Rust / C++
    ("BLOCK", "Cargo.lock"),
    ("ALLOW", "Cargo.toml"),
    ("ALLOW", "src/main.rs"),
    ("BLOCK", "target/debug/build/x.rs"),
    ("ALLOW", "src/target/mod.rs"),
    ("BLOCK", "build/CMakeCache.txt"),
    ("BLOCK", "cmake-build-debug/x.cpp"),
    ("ALLOW", "src/build/config.cpp"),
    ("ALLOW", "CMakeLists.txt"),
    ("ALLOW", "include/app/core.hpp"),
    ("BLOCK", "third_party/json/json.hpp"),
    ("BLOCK", "compile_commands.json"),
    # log của check.py
    ("BLOCK", ".check/py-test.log"),
]


def run(hook: str, tool_input: dict) -> str:
    p = subprocess.run(
        [sys.executable, str(HOOKS / hook)],
        input=json.dumps({"tool_input": tool_input, "cwd": ROOT}).encode("utf-8"),
        capture_output=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": ROOT},
    )
    if p.returncode not in (0, 2):
        return f"ERROR({p.returncode}): {p.stderr.decode('utf-8', 'replace').strip()[:200]}"
    return "BLOCK" if p.returncode == 2 else "ALLOW"


def main() -> int:
    wrong = 0
    total = 0
    for hook, cases, key in (
        ("guard.py", GUARD, "command"),
        ("protect_paths.py", PATHS, "file_path"),
    ):
        print(f"\n== {hook}")
        for expected, value in cases:
            total += 1
            got = run(hook, {key: value})
            ok = got == expected
            wrong += not ok
            print(f"  {'OK   ' if ok else 'SAI  '} {got:<5} {value}")
    print(f"\n{total - wrong}/{total} đúng" + ("" if not wrong else "  <-- xem các dòng SAI"))
    return 0 if not wrong else 1


if __name__ == "__main__":
    sys.exit(main())
