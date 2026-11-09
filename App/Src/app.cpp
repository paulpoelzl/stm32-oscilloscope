#include "app.h"

#include "interrupt_timer.hpp"
#include "led.hpp"
#include "main.h" // CubeMX pin labels (LD2_Pin, ...) and LL headers
#include "uart.hpp"

namespace {
const InterruptTimer timer2{TIM2};
const Led led{LD2_GPIO_Port, LD2_Pin};
const Uart uart2{USART2};
} // namespace

extern "C" void app_main(void) {
#ifdef DEBUG
  LL_DBGMCU_EnableDBGSleepMode();
#endif

  // TIM2 period and NVIC priority are set in CubeMX (lowest preempt priority,
  // so the LED never delays the ADC/DMA path).
  timer2.enableUpdateInterrupt();
  timer2.start();

  uart2.writeText("stm32-oscilloscope: started\r\n");

  while (true) {
    __WFI();
  }
}

extern "C" void TIM2_IRQHandler() {
  if (timer2.clearUpdateFlag()) {
    led.toggle();
  }
}
