#pragma once

#include <cstdint>

#include "stm32f3xx_ll_usart.h"

// Blocking transmitter for a USART that CubeMX has already configured
// (baud rate, frame format, pins). Each byte waits for TXE, so a write
// returns once the last byte is in the shift register, not on the wire.
class Uart {
public:
  explicit Uart(USART_TypeDef *usart) : usart_{usart} {}

  void writeByte(std::uint8_t value) const {
    while (!LL_USART_IsActiveFlag_TXE(usart_)) {}
    LL_USART_TransmitData8(usart_, value);
  }

  void writeText(const char *text) const {
    for (const char *c = text; *c != '\0'; c++) {
      writeByte(static_cast<std::uint8_t>(*c));
    }
  }

private:
  USART_TypeDef *const usart_;
};
