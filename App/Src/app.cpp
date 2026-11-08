#include "app.h"

#include "main.h"  // CubeMX pin labels (LD2_Pin, ...) and LL headers
#include "led.hpp"
#include "interrupt_timer.hpp"

namespace {
    const InterruptTimer timer2{TIM2};
    const Led led{LD2_GPIO_Port, LD2_Pin};
}

extern "C" void app_main(void) {
    LL_TIM_InitTypeDef tim_config;
    LL_TIM_StructInit(&tim_config);
    tim_config.Prescaler = 35999;
    tim_config.CounterMode = LL_TIM_COUNTERMODE_UP;
    tim_config.Autoreload = 999;

    // Lowest preempt priority (group 2: preempt 0..3): the LED must never delay the ADC/DMA path.
    timer2.init(tim_config, NVIC_EncodePriority(NVIC_GetPriorityGrouping(), 3, 0));
    timer2.start();

    while (true) {
        __WFI();
    };
}

extern "C" void TIM2_IRQHandler() {
    if (timer2.clearUpdateFlag()) {
        led.toggle();
    }
}