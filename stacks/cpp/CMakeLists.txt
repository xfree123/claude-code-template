cmake_minimum_required(VERSION 3.20)
project({{PKG}} VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(WARNINGS_AS_ERRORS "Coi warning là lỗi" ON)
option(ENABLE_SANITIZERS "Bật AddressSanitizer + UBSan (GCC/Clang)" OFF)

# Cờ warning dùng chung, gắn vào mọi target của project
add_library({{PKG}}_warnings INTERFACE)
if(MSVC)
  target_compile_options({{PKG}}_warnings INTERFACE /W4 /permissive- /utf-8)
  if(WARNINGS_AS_ERRORS)
    target_compile_options({{PKG}}_warnings INTERFACE /WX)
  endif()
else()
  target_compile_options({{PKG}}_warnings INTERFACE
    -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion)
  if(WARNINGS_AS_ERRORS)
    target_compile_options({{PKG}}_warnings INTERFACE -Werror)
  endif()
endif()

if(ENABLE_SANITIZERS AND NOT MSVC)
  add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
  add_link_options(-fsanitize=address,undefined)
endif()

add_library({{PKG}}_core src/core.cpp)
target_include_directories({{PKG}}_core PUBLIC include)
target_link_libraries({{PKG}}_core PRIVATE {{PKG}}_warnings)

add_executable({{PKG}} src/main.cpp)
target_link_libraries({{PKG}} PRIVATE {{PKG}}_core {{PKG}}_warnings)

include(CTest)
if(BUILD_TESTING)
  add_subdirectory(tests)
endif()
