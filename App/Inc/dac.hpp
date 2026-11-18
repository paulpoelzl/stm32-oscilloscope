#pragma once

#include <cstdint>

#include "stm32f3xx_ll_dac.h"

// Run-time control of a DAC channel that CubeMX has already configured
// (trigger, output buffer).
// Pick the output (write(), triangle wave or DMA request), then enable() and
// start the trigger timer last.
class Dac {
public:
  explicit Dac(DAC_TypeDef *dac, std::uint32_t channel)
      : dac_{dac}, channel_{channel} {}

  void enable() const {
    if (LL_DAC_IsEnabled(dac_, channel_)) {
      return;
    }
    LL_DAC_Enable(dac_, channel_);
  }

  void disable() const { LL_DAC_Disable(dac_, channel_); }

  // With the trigger enabled, the value reaches the pin only at the next
  // trigger. Values above 4095 wrap around instead of clipping.
  void write(std::uint16_t value) const {
    LL_DAC_ConvertData12RightAligned(dac_, channel_, value);
  }

  // Each trigger then takes the next value from the DMA instead of write().
  void enableDmaRequest() const { LL_DAC_EnableDMAReq(dac_, channel_); }

  void disableDmaRequest() const { LL_DAC_DisableDMAReq(dac_, channel_); }

  // Counts 0..1023..0, one step per trigger, on top of the value from
  // write(). The sum must stay at or below 4095.
  void enableTriangleWave() const {
    LL_DAC_SetWaveAutoGeneration(dac_, channel_,
                                 LL_DAC_WAVE_AUTO_GENERATION_TRIANGLE);
    LL_DAC_SetWaveTriangleAmplitude(dac_, channel_,
                                    LL_DAC_TRIANGLE_AMPLITUDE_1023);
  }

  void disableTriangleWave() const {
    LL_DAC_SetWaveAutoGeneration(dac_, channel_,
                                 LL_DAC_WAVE_AUTO_GENERATION_NONE);
  }

  std::uint32_t getDataRegAddress() const {
    return LL_DAC_DMA_GetRegAddr(dac_, channel_,
                                 LL_DAC_DMA_REG_DATA_12BITS_RIGHT_ALIGNED);
  }

private:
  DAC_TypeDef *const dac_;
  const std::uint32_t channel_;
};
