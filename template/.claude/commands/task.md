---
description: Chạy một task code theo harness (plan → duyệt → làm → check → ghi lại)
argument-hint: <mô tả task, acceptance checks nếu có>
---

Task: $ARGUMENTS

Làm task trên theo harness dưới đây. Mục tiêu: để lại code chạy được, bằng chứng đã kiểm tra, và CLAUDE.md tốt hơn. Không trò chuyện dài dòng.

## 0. Input
Xác định 5 mục sau từ task, CLAUDE.md và code hiện có:
- Kết quả mong muốn (output)
- Acceptance checks: điều kiện quan sát được để coi là xong (test nào pass, endpoint trả gì, lệnh nào chạy được)
- Phạm vi được sửa (file/thư mục) và phạm vi KHÔNG được động vào
- Tài liệu nguồn (issue, spec, file liên quan)
- Giới hạn: số lần thử, thời gian
Chỉ hỏi tôi khi thiếu thông tin làm thay đổi kết quả. Gom thành MỘT lần hỏi.

Tạo thư mục `docs/runs/<YYYY-MM-DD>-<tên-ngắn>/`, copy 3 file mẫu từ `docs/runs/_template/` vào đó.

## 1. Plan (trước khi sửa bất kỳ file nào)
- Đọc code liên quan trước. Không lên plan dựa trên đoán cấu trúc.
- Viết plan.md: mỗi bước gồm mục tiêu, file đọc, file ghi, check của bước.
- Viết check TRƯỚC khi viết code: nếu được, viết test thất bại trước (test-first) để chứng minh check có ý nghĩa.
- Đánh dấu [SONG SONG] cho bước độc lập, không chung file.
- Đánh dấu [RỦI RO] cho bước: đổi schema/migration, đổi public API, xóa code, đổi config build/deploy.
- DỪNG và chờ tôi duyệt plan.

## 2. Thực thi
- Làm từng bước theo plan. Muốn đổi plan thì nói lý do, cập nhật plan.md, hỏi lại nếu thay đổi lớn.
- Trước bước [RỦI RO]: commit trạng thái hiện tại (hoặc tạo branch) để có điểm phục hồi.
- Chỉ dùng subagent cho việc tìm kiếm/đọc rộng hoặc bước [SONG SONG]. Subagent trả về: đường dẫn, verdict, bằng chứng ngắn. Không 2 agent sửa cùng một file.
- Không thêm dependency, không sửa ngoài phạm vi khi chưa hỏi.

## 3. Xác minh
Chỉ tin tín hiệu thật: test, build, type check, lint, output thực tế của lệnh, screenshot UI.
Sau mỗi bước, ghi vào checks.md:
`bước | yêu cầu | verdict (pass/fail/unresolved) | evidence (lệnh + trích output)`
Không có bằng chứng thì ghi unresolved, không ghi pass.

## 4. Khi fail
- Sửa đúng bước fail, kèm lý do và bằng chứng, phạm vi "chỉ sửa bước này".
- Trong lúc sửa: chạy `python scripts/check.py --failed` (chỉ chạy lại bước đang fail, tự kèm build cần thiết).
- Output của check.py đã được rút gọn. Chỉ mở `.check/<bước>.log` khi phần tóm tắt không đủ để biết nguyên nhân; đọc phần liên quan, không đọc cả file.
- Lỗi format: chạy lệnh "sửa tự động" mà check.py gợi ý, không sửa tay từng chỗ.
- Không thêm `| head`/`| tail` sau check.py: output đã gọn, cắt thêm có thể làm mất dòng lỗi.
- Tối đa 3 lần thử cho một bước. Quá 3 lần: dừng, ghi rõ vào progress.md, báo tôi.
- Không xóa/skip/sửa test để lấy pass. Không thêm try/except nuốt lỗi để lấy pass.

## 5. Hoàn tất
Checklist, mỗi mục có bằng chứng:
- [ ] `python scripts/check.py` (đầy đủ, KHÔNG có --failed/--only) exit 0 trên trạng thái cuối (dán dòng tổng kết)
- [ ] Mọi acceptance check có verdict pass, hoặc ghi rõ unresolved và lý do
- [ ] `git diff --stat` chỉ chứa file trong phạm vi
- [ ] progress.md cập nhật
- [ ] Rule mới (nếu có) đã đề xuất cho CLAUDE.md, mục "Rules đã học" — hỏi tôi trước khi ghi

## 6. Handoff
Cập nhật progress.md sau mỗi giai đoạn: bước đã xong / đang làm / bị chặn, file đã thay đổi, quyết định và lý do, vấn đề mở, bước tiếp theo.

## Báo cáo cuối (ngắn)
- Đã làm gì (1–3 dòng)
- Pass / unresolved / fail
- File đã đổi (`git diff --stat`)
- Đề xuất rule cho CLAUDE.md (nếu có)
Không tự commit/push trừ khi tôi yêu cầu.
