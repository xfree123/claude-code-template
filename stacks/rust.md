## Stack: Rust
- Toolchain qua rustup. Cần component: `rustup component add rustfmt clippy`.
- Build: `cargo build`. Test: `cargo test`. Lint: `cargo clippy --all-targets -- -D warnings`. Format: `cargo fmt`.
- Chạy local: `cargo run` (TODO: thêm tham số nếu có).
- Thêm dependency: `cargo add <crate>` (cần hỏi người dùng). Không sửa tay Cargo.lock.

### Quy ước
- Không `unwrap()` trong code chính (clippy cảnh báo qua `[lints]` trong Cargo.toml); test thì được phép. Dùng `?` và trả `Result`.
- Lỗi: thư viện dùng `thiserror` (enum lỗi có nghĩa); binary dùng `anyhow` + `.context("...")`.
- `unsafe` bị cấm (`unsafe_code = "forbid"`). Cần FFI/unsafe thì hỏi người dùng, cô lập trong module riêng, mỗi khối có comment `// SAFETY:` giải thích bất biến.
- Không `clone()` để né borrow checker khi chưa hiểu nguyên nhân; nói rõ lý do nếu cần clone.
- Không thêm `#[allow(...)]` để tắt lint khi chưa hỏi.
- Logging: `tracing` (structured), không `println!` trong code thư viện.
- Async (nếu dùng): một runtime duy nhất (tokio); không gọi blocking I/O trong async, dùng `spawn_blocking`.
- Unit test đặt trong `#[cfg(test)] mod tests` ở CUỐI file; integration test trong `tests/`.
