#include "app.h"

#include "adc.hpp"
#include "dac.hpp"
#include "dma_channel.hpp"
#include "interrupt_timer.hpp"
#include "led.hpp"
#include "main.h" // CubeMX pin labels (LD2_Pin, ...) and LL headers
#include "sample_buffer.hpp"
#include "uart.hpp"
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <numbers>
#include <span>

namespace {
const InterruptTimer timer2{TIM2};
const Timer timer3{TIM3};
const Timer timer6{TIM6};
const Led led{LD2_GPIO_Port, LD2_Pin};
const Uart uart2{USART2};
const Adc adc1{ADC1};
const DmaChannel channel1{DMA1, LL_DMA_CHANNEL_1};
const Dac dac1{DAC1, LL_DAC_CHANNEL_1};
const DmaChannel channel3{DMA1, LL_DMA_CHANNEL_3};

constexpr std::size_t kSampleCount = 256;
constexpr std::size_t kSineLength = 64;

constinit SampleBuffer<kSampleCount> adcBuffer;
constinit std::array<std::uint16_t, kSineLength> sineTable{};
std::uint16_t reportedOverrun{};

// One period, centred in the 12-bit range.
void fillSineTable() {
  constexpr float kMidpoint = 2048.0f;
  constexpr float kAmplitude = 2000.0f;
  constexpr float kStep = 2.0f * std::numbers::pi_v<float> / kSineLength;
  for (std::size_t i = 0; i < sineTable.size(); i++) {
    float value =
        kMidpoint + kAmplitude * std::sin(static_cast<float>(i) * kStep);
    sineTable[i] = static_cast<std::uint16_t>(std::lround(value));
  }
}

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

  fillSineTable();
  channel3.setPeriphAddress(dac1.getDataRegAddress());
  channel3.setMemoryAddress(sineTable.data());
  channel3.setDataLength(sineTable.size());
  channel3.enable();

  dac1.enableDmaRequest();
  dac1.enable();

  // 72 MHz / 22500 = 3.2 kHz trigger, / 64 points = 50 Hz sine.
  timer6.setTimebase(0, 22499);
  timer6.start();

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
