# Test không phụ thuộc thư viện ngoài để build được cả khi offline.
# Muốn dùng GoogleTest/Catch2: xem phần "Test" trong CLAUDE.md.
add_executable({{PKG}}_tests test_core.cpp)
target_link_libraries({{PKG}}_tests PRIVATE {{PKG}}_core {{PKG}}_warnings)
add_test(NAME {{PKG}}_tests COMMAND {{PKG}}_tests)
