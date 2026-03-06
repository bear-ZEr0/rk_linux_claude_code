---
name: cpp-testing
description: C++ 测试 - 使用 Google Test 进行 C++ 单元测试和集成测试
---

# C++ 测试

## 何时激活

- 用户请求编写 C++ 测试
- 用户使用 `/tdd` 且目标为 C++ 代码
- 用户提到 Google Test、gtest、gmock

## 测试框架

### Google Test（推荐）

适用于 C++ 项目的单元测试和集成测试。

```cpp
#include <gtest/gtest.h>
#include "spi_driver.h"

class SpiDriverTest : public ::testing::Test {
protected:
    void SetUp() override {
        driver_ = std::make_unique<SpiDriver>();
    }

    void TearDown() override {
        driver_.reset();
    }

    std::unique_ptr<SpiDriver> driver_;
};

TEST_F(SpiDriverTest, InitWithValidConfig) {
    SpiConfig config{.baudRate = 1000000, .mode = SpiMode::Mode0};
    EXPECT_EQ(driver_->init(config), 0);
}

TEST_F(SpiDriverTest, InitWithZeroBaudRateReturnsError) {
    SpiConfig config{.baudRate = 0, .mode = SpiMode::Mode0};
    EXPECT_EQ(driver_->init(config), -EINVAL);
}
```

### Google Mock

用于模拟硬件抽象层接口。

```cpp
#include <gmock/gmock.h>
#include "i_gpio.h"

class MockGpio : public IGpio {
public:
    MOCK_METHOD(void, set, (uint8_t pin, bool value), (override));
    MOCK_METHOD(bool, get, (uint8_t pin), (const, override));
};

TEST_F(LedControllerTest, TurnOnSetsGpioHigh) {
    MockGpio gpio;
    LedController led(gpio, LED_PIN);

    EXPECT_CALL(gpio, set(LED_PIN, true)).Times(1);
    led.turnOn();
}
```

## CMake 集成

```cmake
# 获取 Google Test
include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
)
FetchContent_MakeAvailable(googletest)

# 添加测试
enable_testing()

add_executable(unit_tests
    test_spi_driver.cpp
    test_led_controller.cpp
)

target_link_libraries(unit_tests
    GTest::gtest_main
    GTest::gmock
    project_lib
)

include(GoogleTest)
gtest_discover_tests(unit_tests)
```

## 构建与运行

```bash
# 构建测试
mkdir -p build && cd build
cmake .. -DBUILD_TESTING=ON
make -j$(nproc)

# 运行所有测试
ctest --output-on-failure

# 运行指定测试
./unit_tests --gtest_filter="SpiDriverTest.*"

# 生成覆盖率（需 gcov）
cmake .. -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS="--coverage"
make -j$(nproc) && ctest
gcovr --html-details coverage.html
```

## 测试模式

### 参数化测试

```cpp
class BaudRateTest : public ::testing::TestWithParam<uint32_t> {};

TEST_P(BaudRateTest, ValidBaudRates) {
    SpiConfig config{.baudRate = GetParam()};
    EXPECT_EQ(spi_init(config), 0);
}

INSTANTIATE_TEST_SUITE_P(
    SpiSuite, BaudRateTest,
    ::testing::Values(9600, 115200, 1000000, 4000000)
);
```

### 类型参数化测试

```cpp
template <typename T>
class BufferTest : public ::testing::Test {
protected:
    T buffer_;
};

using BufferTypes = ::testing::Types<
    StaticBuffer<64>,
    StaticBuffer<256>,
    StaticBuffer<1024>
>;

TYPED_TEST_SUITE(BufferTest, BufferTypes);

TYPED_TEST(BufferTest, InitiallyEmpty) {
    EXPECT_TRUE(this->buffer_.empty());
    EXPECT_EQ(this->buffer_.size(), 0);
}
```

## 嵌入式适配

- 使用接口类（纯虚类）抽象硬件依赖
- 通过依赖注入实现可测试性
- 测试在主机（x86）上运行，不依赖目标硬件
- 使用 `--gtest_filter` 区分主机测试和板级测试
