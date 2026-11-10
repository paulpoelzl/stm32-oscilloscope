#include "app.h"

#include "adc.hpp"
#include "dma_channel.hpp"
#include "interrupt_timer.hpp"
#include "led.hpp"
#include "main.h" // CubeMX pin labels (LD2_Pin, ...) and LL headers
#include "sample_buffer.hpp"
#include "uart.hpp"
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <span>

namespace {
const InterruptTimer timer2{TIM2};
const Timer timer3{TIM3};
const Led led{LD2_GPIO_Port, LD2_Pin};
const Uart uart2{USART2};
const Adc adc1{ADC1};
const DmaChannel channel1{DMA1, LL_DMA_CHANNEL_1};

constexpr std::size_t kSampleCount = 256;

constinit SampleBuffer<kSampleCount> adcBuffer;
std::uint16_t reportedOverrun{};

char text[16];
void sendSamples(std::span<const volatile std::uint16_t> samples) {
  for (auto sample : samples) {
    std::snprintf(text, sizeof(text), "%u\r\n", sample);
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
    if (!adcBuffer.hasReadyHalf()) {
      __WFI();
    }
    __enable_irq();

    std::uint16_t localOverrun = adcBuffer.overrunCount();
    if (localOverrun != reportedOverrun) {
      reportedOverrun = localOverrun;
      uart2.writeText("Overrun: ");
      std::snprintf(text, sizeof(text), "%u\r\n", reportedOverrun);
      uart2.writeText(text);
    } else if (adcBuffer.hasReadyHalf()) {
      sendSamples(adcBuffer.getReadyHalf());
      adcBuffer.release();
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

// HT: lower half full, TC: upper half full.
extern "C" void DMA1_Channel1_IRQHandler() {
  if (channel1.clearHTFlag()) {
    adcBuffer.markLowerReady();
  }
  if (channel1.clearTCFlag()) {
    adcBuffer.markUpperReady();
  }
}
