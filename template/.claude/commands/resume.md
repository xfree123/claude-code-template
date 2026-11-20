---
description: Tiếp tục task dở dang từ docs/runs
argument-hint: [tên thư mục run, bỏ trống = run mới nhất]
---

Tiếp tục task dở dang.

1. Xác định thư mục run: `$ARGUMENTS` nếu có, nếu không thì thư mục mới nhất trong `docs/runs/` (bỏ qua `_template`).
2. Đọc theo thứ tự: CLAUDE.md, plan.md, progress.md, checks.md của run đó.
3. Chạy `git status` và `git log --oneline -5` để xác nhận code khớp với progress.md. Nếu lệch (ai đó đã sửa), báo tôi trước khi làm tiếp.
4. Tóm tắt trong 3 dòng: đang ở bước nào, cái gì đã pass, bước tiếp theo.
5. Làm tiếp theo đúng quy trình của `/task` (mục 2–6).
