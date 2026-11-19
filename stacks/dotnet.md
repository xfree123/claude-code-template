## Stack: .NET
- Solution: TODO (ví dụ `src/App.sln`). Nếu có nhiều .sln, khai báo `dotnet_target` trong `scripts/check.config.json`.
- Build: `dotnet build`. Test: `dotnet test`. Format: `dotnet format` (theo `.editorconfig`).
- Chạy local: TODO (ví dụ `dotnet run --project src/App.Api`).

### Quy ước
- `<Nullable>enable</Nullable>`; không dùng `!` để tắt cảnh báo null khi chưa hiểu nguyên nhân.
- async/await xuyên suốt; không `.Result`, `.Wait()`, `async void` (trừ event handler).
- Truyền `CancellationToken` cho mọi hàm async ở tầng API/service.
- Dependency injection qua constructor; không `new` service trong controller.
- Logging qua `ILogger<T>` với structured logging (`{OrderId}`), không nối chuỗi.
- Cấu hình qua `IOptions<T>`; secret dùng User Secrets (dev) / biến môi trường (prod), không ghi vào appsettings.json.

### Database (EF Core)
- Đổi model -> tạo migration bằng `dotnet ef migrations add <Tên>` (lệnh này cần hỏi người dùng). Không sửa tay file trong `Migrations/`.
- Không chạy `dotnet ef database update` — hook chặn. Người dùng tự apply.
- Query: dùng `AsNoTracking()` cho truy vấn chỉ đọc; tránh N+1 (dùng `Include` hoặc projection).
