#include "app.h"

#include "adc.hpp"
#include "dma_channel.hpp"
#include "interrupt_timer.hpp"
#include "led.hpp"
#include "main.h" // CubeMX pin labels (LD2_Pin, ...) and LL headers
#include "uart.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>

namespace {
const InterruptTimer timer2{TIM2};
const Timer timer3{TIM3};
const Led led{LD2_GPIO_Port, LD2_Pin};
const Uart uart2{USART2};
const Adc adc1{ADC1};
const DmaChannel channel1{DMA1, LL_DMA_CHANNEL_1};

constexpr std::size_t kSampleCount = 256;
static_assert(kSampleCount % 2 == 0,
              "HT splits the buffer into two equal halves");
static_assert(kSampleCount <= 0xFFFF, "CNDTR is a 16-bit counter");

// Written by the DMA, which the compiler can't see; volatile forces real reads.
std::array<volatile std::uint16_t, kSampleCount> adcBuffer;
volatile bool lowerHalfReady{};
volatile bool upperHalfReady{};
volatile std::uint16_t overrun{};
std::uint16_t reportedOverrun{};

char text[10];
void sendSamples(std::size_t first, std::size_t last) {
  for (std::size_t i = first; i < last; i++) {
    std::snprintf(text, sizeof(text), "%d\r\n", adcBuffer[i]);
    uart2.writeText(text);
  }
}
} // namespace

extern "C" void app_main(void) {
#ifdef DEBUG
  LL_DBGMCU_EnableDBGSleepMode();
#endif

  channel1.setPeriphAddress(adc1.getDataRegAddress());
  channel1.setMemoryAddress(adcBuffer.data());
  channel1.setDataLength(adcBuffer.size());
  channel1.enableInterrupts();
  channel1.enable();

  // TIM2 period and NVIC priority are set in CubeMX (lowest preempt priority,
  // so the LED never delays the ADC/DMA path).
  timer2.enableUpdateInterrupt();
  timer2.start();

  adc1.enable();
  adc1.start();
  timer3.start();

  uart2.writeText("stm32-oscilloscope: started\r\n");

  while (true) {
    // WFI still wakes on a pending interrupt with PRIMASK set,
    // so an ISR that fires after the check isn't missed.
    __disable_irq();
    if (!lowerHalfReady && !upperHalfReady && overrun == reportedOverrun) {
      __WFI();
    }
    __enable_irq();

    std::uint16_t localOverrun = overrun;
    if (localOverrun > reportedOverrun) {
      reportedOverrun = localOverrun;
      uart2.writeText("Overrun: ");
      std::snprintf(text, sizeof(text), "%d\r\n", localOverrun);
      uart2.writeText(text);
    } else if (lowerHalfReady) {
      sendSamples(0, adcBuffer.size() / 2);
      lowerHalfReady = false;
    } else if (upperHalfReady) {
      sendSamples(adcBuffer.size() / 2, adcBuffer.size());
      upperHalfReady = false;
    }
  }
}

// IRQ handler generation is off for TIM2 and DMA1_Channel1 in CubeMX,
// so they are defined here.
extern "C" void TIM2_IRQHandler() {
  if (timer2.clearUpdateFlag()) {
    led.toggle();
  }
}

// The DMA starts overwriting the lower half at TC and the upper at HT,
// so a mark still set there is an overrun.
extern "C" void DMA1_Channel1_IRQHandler() {
  if (channel1.clearHTFlag()) {
    if (upperHalfReady) {
      overrun = overrun + 1;
    }
    lowerHalfReady = true;
  }
  if (channel1.clearTCFlag()) {
    if (lowerHalfReady) {
      overrun = overrun + 1;
    }
    upperHalfReady = true;
  }
}
