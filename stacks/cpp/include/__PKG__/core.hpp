#pragma once

#include <cstdint>

namespace {{PKG}} {

/// Ví dụ để kiểm tra khung project; xóa khi viết code thật.
[[nodiscard]] std::int64_t add(std::int64_t a, std::int64_t b) noexcept;

} // namespace {{PKG}}
