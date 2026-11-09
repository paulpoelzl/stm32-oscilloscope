#pragma once

#include "stm32f3xx_ll_tim.h"
#include "timer.hpp"

// Timer that raises the update interrupt once per period.
// The NVIC priority and enable come from CubeMX; this class only switches the
// timer's own update interrupt on and off.
// The ISR must call clearUpdateFlag() first and do the application work only if it returns true.
//
// Shared vectors: TIM1 and TIM16 share TIM1_UP_TIM16, TIM15 and TIM17 share theirs with
// other TIM1 interrupts, and TIM6/TIM7 share theirs with the DAC. For these, the ISR
// must check every source on that vector, not just this timer.
class InterruptTimer : public Timer {
	public:
		using Timer::Timer;

		// Clears the update flag left over from the init so the first interrupt
		// comes after a full period, not immediately.
		void enableUpdateInterrupt() const {
			LL_TIM_ClearFlag_UPDATE(timer_);
			LL_TIM_EnableIT_UPDATE(timer_);
		}
		void disableUpdateInterrupt() const { LL_TIM_DisableIT_UPDATE(timer_); }

		// Returns true if an update event was pending (and clears it).
		bool clearUpdateFlag() const {
			if (LL_TIM_IsActiveFlag_UPDATE(timer_)) {
				LL_TIM_ClearFlag_UPDATE(timer_);
				return true;
			}
			return false;
		}
};