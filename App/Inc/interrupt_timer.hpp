#pragma once

#include "timer.hpp"

// Timer that raises the update interrupt once per period.
// The ISR must call clearUpdateFlag() first and do the application work only if it returns true.
//
// Shared vectors: TIM1 and TIM16 share TIM1_UP_TIM16, TIM15 and TIM17 share theirs with
// other TIM1 interrupts, and TIM6/TIM7 share theirs with the DAC. For these:
// - the ISR must check every source on that vector, not just this timer
// - the NVIC priority belongs to the vector, so the last init() wins
// - disabling the IRQ in the NVIC disables it for every source on the vector
class InterruptTimer : public Timer {
	public:
		using Timer::Timer;

		// priority: encoded NVIC priority, e.g. from NVIC_EncodePriority()
		void init(const LL_TIM_InitTypeDef &config, uint32_t priority) const {
			Timer::init(config);
			LL_TIM_ClearFlag_UPDATE(timer_);
			LL_TIM_EnableIT_UPDATE(timer_);
			IRQn_Type interrupt = getGlobalInterrupt();
			NVIC_SetPriority(interrupt, priority);
			NVIC_EnableIRQ(interrupt);
		}

		// Returns true if an update event was pending (and clears it).
		bool clearUpdateFlag() const {
			if (LL_TIM_IsActiveFlag_UPDATE(timer_)) {
				LL_TIM_ClearFlag_UPDATE(timer_);
				return true;
			}
			return false;
		}

	private:
		// Maps the timer to its NVIC vector for the update interrupt.
		IRQn_Type getGlobalInterrupt() const {
			if (timer_ == TIM1)
				return TIM1_UP_TIM16_IRQn;
			if (timer_ == TIM2)
				return TIM2_IRQn;
			if (timer_ == TIM3)
				return TIM3_IRQn;
			if (timer_ == TIM6)
				return TIM6_DAC1_IRQn; 
			if (timer_ == TIM7)
				return TIM7_IRQn;
			if (timer_ == TIM15)
				return TIM15_IRQn;
			if (timer_ == TIM16)
				return TIM16_IRQn;
			if (timer_ == TIM17)
				return TIM17_IRQn;
			
			Error_Handler();
			return TIM2_IRQn;
		}
};