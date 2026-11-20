# Changelog

## v1.1.0
- `check.py` tiết kiệm token: bước pass in 1 dòng; bước fail chỉ in dòng lỗi (tối đa `output_lines`), gộp lỗi trùng, lọc nhiễu compiler, rút gọn đường dẫn; log đầy đủ ở `.check/<bước>.log`.
- Công cụ được gọi ở chế độ output ngắn: ruff concise, pytest `--tb=short`, clippy short, rustfmt chỉ liệt kê file, dotnet bỏ summary trùng, tắt màu và backtrace Rust.
- Tóm tắt riêng cho pytest và cargo test (giữ giá trị left/right của assert).
- `--failed` / `--only`: chạy lại đúng bước đang sửa, tự kèm configure/build cần thiết.
- Clippy fail vì lint không còn chặn `cargo test`; chỉ chặn khi có lỗi compile.
- Gợi ý lệnh sửa tự động cho lỗi format.
- `/task` dùng `--failed` khi sửa và bắt buộc chạy đầy đủ trước khi báo xong.
- Hook bảo vệ thư mục `.check/`; `selftest.py` 84 tình huống.

## v1.0.0
- Slash command `/task`, `/resume`, `/learn`, `/onboard`.
- Hook `guard.py`, `protect_paths.py`, `format.py` (Python, chạy trên Windows/Linux/macOS).
- `check.py` tự nhận diện Python, .NET, Rust, C++ (CMake); chế độ `lint_scope: changed` cho project cũ.
- `new_project.py`: tạo project mới kèm khung code, `--apply` vào project có sẵn (không ghi đè), `--update` nâng cấp harness.
