---
description: Áp harness cho project đã có code — khảo sát, điền CLAUDE.md, lập baseline check
---

Project này đã có code, vừa được thêm harness. Thiết lập harness cho khớp với code thật. KHÔNG sửa code nghiệp vụ trong lệnh này.

## 1. Khảo sát (chỉ đọc)
- Cấu trúc thư mục, solution/project, entry point, cách chạy local, cách chạy test.
- Quy ước đang dùng thật trong code (naming, async, DI, logging, cấu hình, ORM, thư mục migration).
- File cấu hình formatter/linter có sẵn: `.editorconfig`, `pyproject.toml`, `ruff.toml`, `Directory.Build.props`, `.clang-format`, `.clang-tidy`, `rustfmt.toml`, `clippy.toml`.
- Đọc README và tài liệu có sẵn.

## 2. Chạy baseline
- Chạy `python scripts/check.py --list` rồi `python scripts/check.py --all`.
- Ghi kết quả vào `docs/baseline.md`: bước nào pass, bước nào fail, số lỗi lint/format, số test fail (tên test). Cần chi tiết thì đọc `.check/<bước>.log`.
- KHÔNG sửa gì để baseline pass.

## 3. Đề xuất cấu hình (cho tôi xem trước khi ghi)
- `CLAUDE.md`: điền các mục TODO bằng thông tin thật đã khảo sát (stack, lệnh chạy, quy ước). Nếu có `CLAUDE.harness.md` (bản mẫu) thì gộp vào CLAUDE.md hiện có rồi đề xuất xóa file mẫu. Quy ước phải lấy từ code hiện có, không áp quy ước mẫu nếu code đang làm khác — nếu khác thì liệt kê để tôi chọn.
- `scripts/check.config.json`:
  - Nếu lint/format đang fail nhiều trên code cũ: `"lint_scope": "changed"` (chỉ kiểm tra file sửa mới).
  - Nếu build có warning cũ: giữ `dotnet_warnaserror: false`.
  - Test đang fail sẵn: KHÔNG skip. Liệt kê trong `docs/baseline.md` mục "Test fail có sẵn" để tôi quyết định.
  - Nhiều solution: đặt `dotnet_target`.
  - Rust có clippy warning cũ: `"rust_deny_warnings": false` (vẫn fail khi có lỗi deny-level).
  - C++: build dir khác `build/` thì đặt `cmake_build_dir`; có CMakePresets.json thì đặt `cmake_preset`; tham số configure riêng (toolchain vcpkg, option) đặt trong `cmake_args`; code vendored đặt trong `cpp_exclude`.
  - C++ chưa có `.clang-format`/`.clang-tidy`: KHÔNG tự thêm (sẽ làm toàn bộ code cũ fail). Đề xuất riêng để tôi quyết định.
  - Build C++ có warning cũ và project đang dùng -Werror/WX: ghi vào baseline, không tự tắt.
- `.claude/hooks/protect_paths.py`: đề xuất thêm thư mục/file cần bảo vệ riêng của project (ví dụ thư mục generated code, file cấu hình môi trường).

## 4. Xác nhận
Sau khi tôi duyệt và bạn ghi file: chạy lại `python scripts/check.py`. Mục tiêu: exit 0 với cấu hình baseline, hoặc chỉ fail ở các test đã liệt kê trong baseline.
Báo cáo ngắn: stack nhận diện được, baseline, cấu hình đã ghi, việc tôi cần quyết định.
