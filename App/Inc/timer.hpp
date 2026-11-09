#pragma once

#include "stm32f3xx_ll_tim.h"

// Run-time control of a timer that CubeMX has already configured
// (clock, prescaler, period, counter mode).
// Special functions (interrupts, PWM, trigger output) go in derived classes.
class Timer {
	public:
		explicit Timer(TIM_TypeDef* timer) : timer_{timer} {}

		void start() const { LL_TIM_EnableCounter(timer_); }
		void stop() const { LL_TIM_DisableCounter(timer_); }

		// Changes the period. Running: PSC and ARR switch together at the next update
		// (needs ARR preload, set in CubeMX). Stopped: applied immediately via UG.
		void setTimebase(uint16_t psc, uint32_t arr) const {
			LL_TIM_SetPrescaler(timer_, psc);
			LL_TIM_SetAutoReload(timer_, arr);
			if (!LL_TIM_IsEnabledCounter(timer_)) {
				LL_TIM_GenerateEvent_UPDATE(timer_);
				LL_TIM_ClearFlag_UPDATE(timer_);
			}
		}

	protected:
		TIM_TypeDef* const timer_;
};