## Stack: Python
- Python >= 3.10, virtualenv ở `.venv/` (Windows: `.venv\Scripts\activate`, Git Bash: `source .venv/Scripts/activate`).
- Cài dependency: `python -m pip install -e ".[dev]"` (hoặc `-r requirements.txt`). Luôn gọi `python -m pip`, không gọi `pip` trần.
- Lint/format: ruff. Type: mypy (nếu cài). Test: pytest.
- Code nằm trong `src/<package>/`, test trong `tests/`.

### Quy ước
- Type hint cho mọi hàm public.
- Dùng `logging`, không dùng `print` trong code thư viện.
- Đọc cấu hình từ biến môi trường / `.env` (python-dotenv), không hard-code secret.
- Mở file luôn chỉ định `encoding="utf-8"` (Windows mặc định không phải UTF-8).
