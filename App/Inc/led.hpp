#pragma once

#include <cstdint>

#include "stm32f3xx_ll_gpio.h"

// Thin wrapper around a push-pull GPIO output. Pin configuration is done by CubeMX.
class Led {
public:
    Led(GPIO_TypeDef* port, std::uint32_t pin) : port_{port}, pin_{pin} {}

    void on() const { LL_GPIO_SetOutputPin(port_, pin_); }
    void off() const { LL_GPIO_ResetOutputPin(port_, pin_); }
    void toggle() const { LL_GPIO_TogglePin(port_, pin_); }

private:
    GPIO_TypeDef* port_;
    std::uint32_t pin_;
};
