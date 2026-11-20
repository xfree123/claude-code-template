# {{PROJECT_NAME}}

> Claude Code tự đọc file này ở đầu mọi phiên. Giữ ngắn, chỉ ghi điều Claude cần biết để làm đúng.
> Sửa các dòng còn TODO ngay khi khởi tạo project.

## Mô tả
{{PROJECT_DESC}}

## Môi trường
- Máy dev: Windows. Lệnh shell chạy qua Git Bash; ưu tiên lệnh chạy được cả Windows và Linux.
- Đường dẫn trong code: dùng `pathlib` / `Path.Combine`, không nối chuỗi với `\` hay `/`.
- Kiểm tra toàn bộ: `python scripts/check.py` (exit 0 = xong). Khi đang sửa lỗi: `python scripts/check.py --failed`.

{{STACK_SECTION}}

## Quy trình làm việc
- Task không nhỏ (sửa > 1 file, tính năng mới, refactor): dùng `/task <mô tả>`.
- Tiếp tục task dở: `/resume`.
- Sửa nhỏ, rõ ràng: làm thẳng, nhưng vẫn chạy `python scripts/check.py` trước khi báo xong.
- "Xong" = `python scripts/check.py` (đầy đủ, không --failed/--only) exit 0. Không báo xong dựa trên suy đoán.
- Không thêm dependency mới khi chưa hỏi.
- Không sửa, skip hay xóa test để lấy pass. Test sai thì nói rõ và hỏi.

## Hooks và script (thực thi tự động, không phải hướng dẫn)
- `.claude/hooks/guard.py` (trước Bash/PowerShell): chặn xóa ngoài project, git force/reset --hard, push main, đọc .env/key, `dotnet ef database update`, publish package (npm/nuget/cargo), `cargo install`, `cmake --install`/`make install`, sudo, đổi cấu hình Windows.
- `.claude/hooks/protect_paths.py` (trước Edit/Write): chặn sửa .env*, key, lockfile (kể cả Cargo.lock), appsettings.Production.json, bin/, obj/, Migrations/, .git/, .claude/hooks/; ở gốc project: target/, build/, out/, third_party/, vendor/.
- `.claude/hooks/format.py` (sau Edit/Write): ruff cho .py, dotnet format cho .cs, rustfmt cho .rs, clang-format cho C/C++ (chỉ khi có .clang-format).
- `scripts/check.py`: lint + format + build + test, tự nhận diện stack (Python, .NET, Rust, C++/CMake). Output đã rút gọn; log đầy đủ ở `.check/<bước>.log`. Cấu hình: `scripts/check.config.json`.

## Rules đã học
<!-- Mỗi khi Claude làm sai và được sửa: thêm 1 dòng "bối cảnh -> rule". Dùng /learn. -->
