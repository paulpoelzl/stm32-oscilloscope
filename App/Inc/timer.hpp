#pragma once

#include "main.h"
#include "stm32f3xx_ll_tim.h"
#include "stm32f3xx_ll_bus.h"

// Base timer: enables the peripheral clock, sets up the time base
// (prescaler, counter mode, period) and starts/stops the counter.
// Special functions (interrupts, PWM, trigger output) go in derived classes.
class Timer {
	public:
		explicit Timer(TIM_TypeDef* timer) : timer_{timer} {}

		void init(const LL_TIM_InitTypeDef &config) const {
			enableClock();
			LL_TIM_Init(timer_, &config);
			LL_TIM_SetClockSource(timer_, LL_TIM_CLOCKSOURCE_INTERNAL);
			LL_TIM_DisableARRPreload(timer_);
			LL_TIM_DisableMasterSlaveMode(timer_);
		}

		void start() const { LL_TIM_EnableCounter(timer_); }
		void stop() const { LL_TIM_DisableCounter(timer_); }

	protected:
		TIM_TypeDef* const timer_;
	
	private:
		void enableClock() const {
			if (timer_ == TIM2)
				LL_APB1_GRP1_EnableClock(LL_APB1_GRP1_PERIPH_TIM2);
			else if (timer_ == TIM3)
				LL_APB1_GRP1_EnableClock(LL_APB1_GRP1_PERIPH_TIM3);
			else if (timer_ == TIM6)
				LL_APB1_GRP1_EnableClock(LL_APB1_GRP1_PERIPH_TIM6);
			else if (timer_ == TIM7)
				LL_APB1_GRP1_EnableClock(LL_APB1_GRP1_PERIPH_TIM7);
			else if (timer_ == TIM1)
				LL_APB2_GRP1_EnableClock(LL_APB2_GRP1_PERIPH_TIM1);
			else if (timer_ == TIM15)
				LL_APB2_GRP1_EnableClock(LL_APB2_GRP1_PERIPH_TIM15);
			else if (timer_ == TIM16)
				LL_APB2_GRP1_EnableClock(LL_APB2_GRP1_PERIPH_TIM16);
			else if (timer_ == TIM17)
				LL_APB2_GRP1_EnableClock(LL_APB2_GRP1_PERIPH_TIM17);
			else
				Error_Handler(); // Call the CubeMX error handler
		}
};