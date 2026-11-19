#include "{{PKG}}/core.hpp"

#include <cstdlib>
#include <iostream>

namespace {

int failures = 0;

void check(bool ok, const char* expr, int line) {
    if (!ok) {
        std::cerr << "FAIL dòng " << line << ": " << expr << '\n';
        ++failures;
    }
}

} // namespace

#define CHECK(expr) check((expr), #expr, __LINE__)

int main() {
    CHECK({{PKG}}::add(2, 3) == 5);
    CHECK({{PKG}}::add(-1, 1) == 0);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
