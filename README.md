# Claude Code Project Template

Bộ khung để mọi project code (mới hoặc đã có) đều có harness cho Claude Code:
plan trước khi code, kiểm tra bằng tín hiệu thật, hook chặn thao tác nguy hiểm, CLAUDE.md tốt dần theo thời gian.

Chạy trên **Windows**, Linux, macOS. Mọi script viết bằng Python, chỉ dùng thư viện chuẩn: không cần bash, không cần jq.
Hỗ trợ sẵn **Python**, **.NET**, **Rust**, **C++ (CMake)**; Node/Go được nhận diện cơ bản.

---

## 1. Cài đặt một lần (Windows)

Yêu cầu:
- Python >= 3.10, gõ được `python` trong terminal (tick "Add python.exe to PATH" khi cài).
- Git for Windows (Claude Code dùng Git Bash để chạy lệnh và hook).
- .NET SDK nếu làm project .NET.
- Rust: rustup + `rustup component add rustfmt clippy`.
- C++: CMake >= 3.20, compiler C++17 (MSVC/GCC/Clang). Nên có Ninja, clang-format, clang-tidy (Windows: cài LLVM, hoặc dùng bản đi kèm Visual Studio).

```powershell
# Giải nén vào chỗ cố định
Expand-Archive $HOME\Downloads\claude-code-template.zip -DestinationPath $HOME\templates

# Kiểm tra hook chạy đúng trên máy bạn
cd $HOME\templates\claude-code-template
python selftest.py          # phải ra: 82/82 đúng
```

Tạo lệnh tắt `newproj` cho PowerShell:

```powershell
notepad $PROFILE
# thêm dòng sau, lưu, mở terminal mới:
function newproj { python "$HOME\templates\claude-code-template\new_project.py" @args }
```

## 2. Project mới

```powershell
newproj D:\code\tms-report --stack python --desc "Báo cáo TMS hằng ngày"
cd D:\code\tms-report
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
python scripts/check.py      # phải PASS
claude
```

Project .NET:

```powershell
newproj D:\code\shop-api --stack dotnet
cd D:\code\shop-api
dotnet new sln -n ShopApi
dotnet new webapi -n ShopApi.Api -o src/ShopApi.Api
dotnet new xunit  -n ShopApi.Tests -o tests/ShopApi.Tests
dotnet sln add src/ShopApi.Api tests/ShopApi.Tests
dotnet add tests/ShopApi.Tests reference src/ShopApi.Api
python scripts/check.py
```

Project Rust:

```powershell
newproj D:\code\cam-agent --stack rust
cd D:\code\cam-agent
python scripts/check.py      # cargo fmt --check, clippy -D warnings, cargo test
```
Khung tạo sẵn: `Cargo.toml` (cấm `unsafe`, cảnh báo `unwrap()` ngoài test), `clippy.toml`, `src/lib.rs` + `src/main.rs` có sẵn 1 unit test.

Project C++:

```powershell
newproj D:\code\cam-sdk --stack cpp
cd D:\code\cam-sdk
python scripts/check.py      # configure, clang-format, build, clang-tidy, ctest
```
Khung tạo sẵn: `CMakeLists.txt` (C++17, warning là lỗi, tùy chọn sanitizer), `include/<tên>/`, `src/`, `tests/` (test không cần thư viện ngoài, build được khi offline), `.clang-format`, `.clang-tidy`.

Repo nhiều stack: `--stack python,cpp`, `--stack rust,python`...

Muốn đổi khung project (thêm file, đổi chuẩn C++, đổi lint Rust): sửa thẳng file trong `stacks/<stack>/`. Đường dẫn chứa `__PKG__` và nội dung chứa `{{PKG}}`, `{{NAME}}`, `{{CRATE}}`, `{{CRATE_IDENT}}` sẽ được thay bằng tên project.

## 3. Project đã có code

```powershell
cd D:\code\old-api
git checkout -b chore/claude-harness      # làm trên nhánh riêng
newproj --apply .                         # tự nhận diện stack, KHÔNG ghi đè file nào
git status                                # xem file vừa thêm
claude
```
Trong Claude Code gõ: `/onboard`

`--apply` làm gì với file đã có:

| File | Xử lý |
|---|---|
| `CLAUDE.md` đã có | Giữ nguyên. Bản mẫu lưu thành `CLAUDE.harness.md`, `/onboard` sẽ gộp |
| `.gitignore` đã có | Chỉ nối thêm dòng còn thiếu |
| `.claude/settings.json` đã có | Gộp: giữ mọi thứ cũ (env, hook, quyền đã chọn), thêm quyền và hook của harness. Bản gốc lưu ở `settings.json.bak` |
| `.claude/commands/` đã có | Giữ command cũ, chỉ thêm command chưa có |
| `.gitattributes` | Lưu thành `.gitattributes.harness`, không áp dụng (đổi quy tắc xuống dòng trên repo cũ có thể làm hàng loạt file hiện "modified") |
| File khác đã có | Bỏ qua |

`/onboard` sẽ: khảo sát code, chạy baseline, ghi `docs/baseline.md`, đề xuất điền CLAUDE.md theo **quy ước thật đang dùng trong code**, và đề xuất `scripts/check.config.json`. Không sửa code nghiệp vụ.

### Vấn đề lớn nhất của project cũ: code cũ không đạt chuẩn format/lint

Nếu để kiểm tra toàn bộ, `check.py` sẽ fail ngay từ đầu vì code cũ. Claude sẽ hoặc bị kẹt, hoặc tự đi format lại toàn bộ repo, tạo ra một diff hàng nghìn dòng. Giải pháp:

```json
// scripts/check.config.json
{ "lint_scope": "changed" }
```

Khi đó lint/format chỉ kiểm tra **file đã đổi so với main** (cộng file chưa commit). Build và test vẫn chạy toàn bộ. Code mới phải sạch, code cũ để yên. Muốn format lại toàn repo thì làm thành một PR riêng, rồi mới chuyển về `"all"`.

Test đang fail sẵn: không skip. `/onboard` liệt kê chúng trong `docs/baseline.md` để team quyết định.

Riêng với từng ngôn ngữ:
- **Rust**: clippy không giới hạn được theo file. Repo cũ nhiều warning thì đặt thêm `"rust_deny_warnings": false` (vẫn fail khi có lỗi). Lưu ý: sửa `lib.rs`/`main.rs`/`mod.rs` thì rustfmt kiểm cả các module con mà file đó khai báo.
- **C++**: format/tidy chỉ chạy khi repo **đã có** `.clang-format`/`.clang-tidy`. `--apply` không tự thêm hai file này vào repo cũ, vì sẽ làm toàn bộ code cũ fail. Code vendored trong `third_party/` được bỏ qua; thư mục khác thì khai báo `cpp_exclude`.

### Project đã áp harness bản cũ: nâng cấp

```powershell
cd D:\code\camera-station
git checkout -b chore/harness-update
newproj --update .
git diff                                   # xem hook/check.py thay đổi gì
```
`--update` ghi đè các file do harness quản lý (`.claude/hooks/*`, `scripts/check.py`, `.claude/commands/{task,resume,learn,onboard}.md`, mẫu trong `docs/runs/_template/`), gộp quyền/hook mới vào `settings.json`. **Không** đụng `CLAUDE.md`, `check.config.json` và code. Nếu bạn đã tự sửa một command mẫu, `git diff` sẽ cho thấy để khôi phục phần cần giữ.

## 4. Làm việc hằng ngày

| Lệnh | Khi nào |
|---|---|
| `/task <mô tả>` | Mọi việc không nhỏ: tính năng, sửa bug, refactor |
| `/resume` | Tiếp tục task dở |
| `/learn <bài học>` | Claude làm sai, ghi thành rule vĩnh viễn |
| `/onboard` | Lần đầu áp harness cho project cũ |
| `python scripts/check.py` | Định nghĩa "xong" |

Luồng một task:
1. **Shift+Tab** cho đến khi thấy plan mode.
2. `/task thêm API GET /orders/{id}/status, trả 404 khi không có đơn. Check: test mới pass`
3. Claude đọc code, viết `docs/runs/<ngày>-<tên>/plan.md`, dừng chờ duyệt.
4. Đọc plan, sửa nếu cần, duyệt.
5. Claude code từng bước, ghi bằng chứng vào `checks.md`.
6. Báo cáo: pass/unresolved, `git diff --stat`, đề xuất rule mới.
7. Bạn review diff, tự commit.

## 5. Hook chặn những gì

**guard.py** (trước lệnh Bash và PowerShell):
- `rm -r` với đường dẫn tuyệt đối/`~`/`..`/ổ đĩa; `Remove-Item -Recurse` ra ngoài project; `rd /s`, `del /s`; format ổ đĩa
- `git push --force` (cho phép `--force-with-lease`), push thẳng main/master, `reset --hard`, `clean -f`, `checkout -- .`
- `dotnet ef database update/drop`, `DROP DATABASE/TABLE`, `TRUNCATE`
- publish package (npm, twine, nuget, `cargo publish`, conan upload)
- `cargo install`, `rustup default`, `cmake --install`, `make install`/`ninja install`, `vcpkg integrate install`, `cmake -E rm -r` ra ngoài project
- `sudo`, cài toàn cục, `Set-ExecutionPolicy`, sửa registry HKLM, tắt/khởi động lại máy
- đọc/copy `.env`, private key

**protect_paths.py** (trước khi sửa file):
- ngoài project, `.env*` (trừ `.env.example`), key/cert, `secrets.json`, `appsettings.Production.json`, lockfile (kể cả `Cargo.lock`, `vcpkg-lock.json`), `compile_commands.json`
- thư mục ở mọi cấp: `.git/`, `.claude/hooks/`, `bin/`, `obj/`, `node_modules/`, `.venv/`, `Migrations/`
- thư mục chỉ ở gốc project: `target/`, `build/`, `out/`, `cmake-build-*/`, `third_party/`, `vendor/`, `vcpkg_installed/` (để không chặn nhầm `src/build/`...)

Sửa danh sách trong từng file hook theo project. Sau khi sửa, chạy lại `python selftest.py` ở thư mục template.

Giới hạn cần biết: hook kiểm tra chuỗi lệnh. Nó chặn được sai lầm vô ý, không chặn được lệnh cố tình né (ví dụ viết lệnh vào script rồi chạy). Lớp bảo vệ cuối vẫn là bạn đọc plan và review diff.

## 6. check.py

```powershell
python scripts/check.py           # chạy theo cấu hình
python scripts/check.py --list    # xem các bước sẽ chạy
python scripts/check.py --all     # bỏ qua lint_scope, kiểm tra toàn bộ
```

Tự nhận diện:
- **Python**: ruff check, ruff format --check, mypy src (nếu cài), pytest (nếu có test). Tự dùng `.venv` của project.
- **.NET**: `dotnet format --verify-no-changes`, `dotnet build`, `dotnet test`. Nhiều `.sln` thì đặt `dotnet_target`.
- **Rust** (có `Cargo.toml`): `cargo fmt --check` (chế độ changed: `rustfmt --check` từng file), `cargo clippy --all-targets -D warnings`, `cargo test --workspace`.
- **C++** (có `CMakeLists.txt`): `cmake` configure → `clang-format --dry-run` (nếu có `.clang-format`) → `cmake --build` → `clang-tidy` (nếu có `.clang-tidy` và `compile_commands.json`) → `ctest`. Configure hoặc build fail thì tidy/test được SKIP, không báo lỗi dây chuyền.

Cấu hình đầy đủ (`scripts/check.config.json`, mọi khóa đều tùy chọn):

```json
{
  "lint_scope": "changed",
  "base_ref": "origin/develop",
  "dotnet_target": "src/ShopApi.sln",
  "dotnet_warnaserror": false,
  "rust_deny_warnings": true,
  "cmake_build_dir": "build",
  "cmake_build_type": "Debug",
  "cmake_preset": "dev",
  "cmake_args": ["-DENABLE_SANITIZERS=ON", "-DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake"],
  "cpp_exclude": ["third_party/", "external/"],
  "skip": ["py-type", "cpp-tidy"],
  "extra_steps": [
    {"name": "api-smoke", "cmd": ["curl", "-fsS", "http://localhost:5000/health"]}
  ]
}
```
`"steps": [...]` thay hoàn toàn phần tự nhận diện, dùng khi project có cách build đặc biệt.

## 7. Xử lý sự cố

| Triệu chứng | Nguyên nhân / cách sửa |
|---|---|
| Hook không chạy | Trong Claude Code gõ `/hooks` xem có 3 hook không. Kiểm tra `python --version` chạy được trong Git Bash |
| `python` mở Microsoft Store | Tắt App execution alias cho python.exe trong Settings → Apps → Advanced app settings |
| Chỉ có lệnh `py` | Sửa `"command": "python"` thành `"command": "py"` trong `.claude/settings.json` |
| `/permissions` báo lỗi cú pháp | Claude Code đổi cú pháp quyền; sửa theo thông báo |
| check.py: "bỏ qua py-lint: chưa cài ruff" | `python -m pip install ruff` trong .venv |
| .NET build lỗi NU1301 | Không tải được NuGet — kiểm tra mạng/proxy, chạy `dotnet restore` |
| `cpp-tidy` luôn SKIP trên Windows | Generator Visual Studio không sinh `compile_commands.json`. Cài Ninja và chạy check trong "Developer PowerShell for VS", hoặc đặt `"skip": ["cpp-tidy"]` |
| `Does not match the generator used previously` | Thư mục `build/` được configure bằng generator khác. Xóa `build/` rồi chạy lại |
| `rust-clippy` bị bỏ qua | `rustup component add clippy rustfmt` |

## 8. Cập nhật template

Template nằm ở `$HOME\templates\claude-code-template\`. Rule nào lặp lại ở nhiều project (mục "Rules đã học") thì chép ngược về `template/CLAUDE.md` hoặc `stacks/*.md`. Nên đưa thư mục này lên Bitbucket để cả team dùng chung và quản lý phiên bản.

```
claude-code-template/
├── new_project.py            # tạo project / --apply vào project cũ / --update nâng cấp
├── selftest.py               # kiểm tra hook trên máy bạn
├── stacks/
│   ├── python.md  dotnet.md  rust.md  cpp.md   # quy ước, chèn vào CLAUDE.md
│   ├── python/               # khung project mới (pyproject, src/, tests/)
│   ├── rust/                 # Cargo.toml, clippy.toml, src/lib.rs, src/main.rs
│   └── cpp/                  # CMakeLists.txt, include/, src/, tests/, .clang-format, .clang-tidy
└── template/
    ├── CLAUDE.md
    ├── .claude/settings.json
    ├── .claude/commands/     task, resume, learn, onboard
    ├── .claude/hooks/        guard.py, protect_paths.py, format.py
    ├── scripts/check.py
    ├── docs/runs/_template/  plan.md, checks.md, progress.md
    ├── .gitignore  .gitattributes  .env.example
```
