#pragma once

#include <cstdint>

#include "stm32f3xx_ll_adc.h"

// Run-time control of an ADC that CubeMX has already configured (channel,
// sampling time, trigger source, voltage regulator).
// Call enable() once at startup, then start().
class Adc {
public:
  explicit Adc(ADC_TypeDef *adc) : adc_{adc} {}

  // Calibrates first, so it does nothing if the ADC is already enabled.
  void enable() const {
    if (LL_ADC_IsEnabled(adc_)) {
      return;
    }
    calibrate();
    // ADEN is ignored for 4 ADC clock cycles after calibration. ADC clock is
    // HCLK/1, so 4 CPU cycles; x32 leaves margin for a slower ADC clock.
    // __NOP() keeps the compiler from removing the loop.
    for (std::uint32_t i = 0; i < LL_ADC_DELAY_CALIB_ENABLE_ADC_CYCLES * 32;
         i++) {
      __NOP();
    }
    // Hardware never clears ADRDY, so a stale flag would end the wait early.
    LL_ADC_ClearFlag_ADRDY(adc_);
    LL_ADC_Enable(adc_);
    while (!LL_ADC_IsActiveFlag_ADRDY(adc_)) {}
  }

  void disable() const {
    if (!LL_ADC_IsEnabled(adc_)) {
      return;
    }
    stop();
    LL_ADC_Disable(adc_);
    while (LL_ADC_IsEnabled(adc_)) {}
  }

  // With an external trigger, the ADC stays armed until stop().
  void start() const { LL_ADC_REG_StartConversion(adc_); }

  // Aborts a running conversion. Afterwards, trigger, sequence and DMA can be
  // reconfigured without disabling the ADC.
  void stop() const {
    if (LL_ADC_REG_IsConversionOngoing(adc_)) {
      LL_ADC_REG_StopConversion(adc_);
      while (LL_ADC_REG_IsConversionOngoing(adc_)) {}
    }
  }

  // Latest result, without waiting (overrun mode overwrites, see CubeMX).
  std::uint16_t read() const { return LL_ADC_REG_ReadConversionData12(adc_); }

  std::uint32_t getDataRegAddress() const {
    return LL_ADC_DMA_GetRegAddr(adc_, LL_ADC_DMA_REG_REGULAR_DATA);
  }

private:
  // Only runs while the ADC is disabled.
  void calibrate() const {
    LL_ADC_StartCalibration(adc_, LL_ADC_SINGLE_ENDED);
    while (LL_ADC_IsCalibrationOnGoing(adc_)) {}
  }

  ADC_TypeDef *const adc_;
};
