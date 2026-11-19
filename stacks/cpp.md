## Stack: C++ (CMake)
- Chuẩn: C++17 (đổi `CMAKE_CXX_STANDARD` trong CMakeLists.txt nếu compiler hỗ trợ 20).
- Configure: `cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug` (thêm `-G Ninja` nếu có Ninja).
- Build: `cmake --build build --parallel`. Test: `ctest --test-dir build --output-on-failure` (Windows/Visual Studio thêm `-C Debug`).
- Format: clang-format theo `.clang-format`. Lint: clang-tidy theo `.clang-tidy` (cần `build/compile_commands.json`, chỉ có với generator Ninja/Makefiles).
- Không sửa tay trong `build/`, `third_party/`, `vendor/` (hook chặn).

### Quy ước
- RAII cho mọi tài nguyên. Không `new`/`delete` trần: dùng `std::unique_ptr` / `std::make_unique`, `std::vector`, `std::string`.
- Truyền tham số: kiểu nhỏ theo giá trị, kiểu lớn theo `const&`; trả về theo giá trị (để RVO/move làm việc).
- Không `using namespace` trong header. Header dùng `#pragma once`.
- Không C-style cast; dùng `static_cast` và ép kiểu tường minh khi đổi số nguyên có dấu/không dấu (`-Wconversion` đang bật).
- Warning là lỗi (`WARNINGS_AS_ERRORS=ON`). Không tắt warning hay thêm `// NOLINT` khi chưa hỏi.
- Hàm trả giá trị quan trọng: `[[nodiscard]]`. Hàm không ném: `noexcept`.
- Ranh giới module dùng `std::string_view`/`std::span` (C++20) thay cho con trỏ + độ dài.

### Test
- Khung mặc định: một executable tự kiểm tra, đăng ký bằng `add_test` (không cần mạng).
- Chuyển sang GoogleTest khi project lớn hơn: dùng `FetchContent` (cần mạng khi configure) hoặc vcpkg, rồi `gtest_discover_tests()`. Hỏi người dùng trước khi thêm.
- Lỗi bộ nhớ: chạy với `-DENABLE_SANITIZERS=ON` (GCC/Clang) khi nghi ngờ use-after-free, out-of-bounds, UB.
