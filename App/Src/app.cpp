#include "app.h"

#include "main.h"  // CubeMX pin labels (LD2_Pin, ...) and LL headers
#include "led.hpp"
#include "interrupt_timer.hpp"

namespace {
    const InterruptTimer timer2{TIM2};
    const Led led{LD2_GPIO_Port, LD2_Pin};
}

extern "C" void app_main(void) {
    // TIM2 period and NVIC priority are set in CubeMX (lowest preempt priority,
    // so the LED never delays the ADC/DMA path).
    timer2.enableUpdateInterrupt();
    timer2.start();

    while (true) {
        __WFI();
    }
}

extern "C" void TIM2_IRQHandler() {
    if (timer2.clearUpdateFlag()) {
        led.toggle();
    }
}