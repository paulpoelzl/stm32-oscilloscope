#include "app.h"

#include "adc.hpp"
#include "interrupt_timer.hpp"
#include "led.hpp"
#include "main.h" // CubeMX pin labels (LD2_Pin, ...) and LL headers
#include "uart.hpp"
#include <cstdint>
#include <cstdio>

namespace {
const InterruptTimer timer2{TIM2};
const Timer timer3{TIM3};
const Led led{LD2_GPIO_Port, LD2_Pin};
const Uart uart2{USART2};
const Adc adc1{ADC1};
} // namespace

extern "C" void app_main(void) {
#ifdef DEBUG
  LL_DBGMCU_EnableDBGSleepMode();
#endif

  // TIM2 period and NVIC priority are set in CubeMX (lowest preempt priority,
  // so the LED never delays the ADC/DMA path).
  timer2.enableUpdateInterrupt();
  timer2.start();

  adc1.enable();
  adc1.start();
  timer3.start();

  uart2.writeText("stm32-oscilloscope: started\r\n");
  char buffer[10];
  while (true) {
    __WFI();
    std::uint16_t adcVal = adc1.read();

    std::snprintf(buffer, sizeof(buffer), "%d\r\n", adcVal);
    uart2.writeText(buffer);
  }
}

extern "C" void TIM2_IRQHandler() {
  if (timer2.clearUpdateFlag()) {
    led.toggle();
  }
}
