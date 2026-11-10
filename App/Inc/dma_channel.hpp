#pragma once

#include "stm32f3xx_ll_dma.h"
#include <cstdint>

// Run-time control of a DMA channel that CubeMX has already configured
// (direction, data sizes, increment, mode, priority).
// The addresses and the length are set here, since they depend on the
// application's buffers.
class DmaChannel {
public:
  explicit DmaChannel(DMA_TypeDef *dma, std::uint32_t channel)
      : dma_{dma}, channel_{channel} {}

  // The three setters write CPAR, CMAR and CNDTR, which ignore writes while
  // the channel is enabled. Call them before enable().

  void setPeriphAddress(std::uint32_t addr) const {
    LL_DMA_SetPeriphAddress(dma_, channel_, addr);
  }

  // The DMA can't reach CCM RAM, so the buffer must be in normal SRAM.
  void setMemoryAddress(volatile void *addr) const {
    LL_DMA_SetMemoryAddress(dma_, channel_,
                            reinterpret_cast<std::uint32_t>(addr));
  }

  void setDataLength(std::uint32_t len) const {
    LL_DMA_SetDataLength(dma_, channel_, len);
  }

  void enableInterrupts() const {
    LL_DMA_EnableIT_HT(dma_, channel_);
    LL_DMA_EnableIT_TC(dma_, channel_);
  }

  void enable() const { LL_DMA_EnableChannel(dma_, channel_); }

  void disable() const { LL_DMA_DisableChannel(dma_, channel_); }

  bool clearHTFlag() const {
    if (isFlagActive(flagMask(DMA_ISR_HTIF1))) {
      clearFlag(flagMask(DMA_IFCR_CHTIF1));
      return true;
    }
    return false;
  }

  bool clearTCFlag() const {
    if (isFlagActive(flagMask(DMA_ISR_TCIF1))) {
      clearFlag(flagMask(DMA_IFCR_CTCIF1));
      return true;
    }
    return false;
  }

private:
  DMA_TypeDef *const dma_;
  const std::uint32_t channel_;

  // ISR and IFCR hold 4 flag bits per channel; channel 1 is at bits 0-3.
  std::uint32_t flagMask(std::uint32_t ch1Mask) const {
    return ch1Mask << (4 * (channel_ - 1));
  }

  bool isFlagActive(std::uint32_t mask) const { return dma_->ISR & mask; }

  // IFCR is write-1-to-clear; zero bits leave the other flags alone.
  void clearFlag(std::uint32_t mask) const { dma_->IFCR = mask; }
};
