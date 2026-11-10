#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

// Circular DMA buffer of N ADC samples, processed one half at a time.
// The DMA ISR marks a half ready at HT (lower) and TC (upper). The main loop
// processes the ready half, then calls release(). A half that is still marked
// when the DMA starts writing it again counts as an overrun.
template <std::size_t N> class SampleBuffer {
public:
  static_assert(N % 2 == 0, "HT splits the buffer into two equal halves");
  static_assert(N <= 0xFFFF, "CNDTR is a 16-bit counter");

  static constexpr std::size_t size() { return N; }
  volatile std::uint16_t *data() { return buffer_.data(); }

  // Called from the DMA ISR.

  void markLowerReady() {
    if (upperReady_) {
      overrun_ = overrun_ + 1;
    }
    lowerReady_ = true;
  }

  void markUpperReady() {
    if (lowerReady_) {
      overrun_ = overrun_ + 1;
    }
    upperReady_ = true;
  }

  // Called from the main loop.

  // An overrun always leaves a half marked, so this also covers overruns.
  bool hasReadyHalf() const { return lowerReady_ || upperReady_; }

  // Lower half first; empty if neither is ready. Doesn't release the half.
  std::span<const volatile std::uint16_t> getReadyHalf() {
    std::span<const volatile std::uint16_t> all = buffer_;
    if (lowerReady_) {
      handedOut_ = Half::Lower;
      return all.first(N / 2);
    }
    if (upperReady_) {
      handedOut_ = Half::Upper;
      return all.last(N / 2);
    }
    handedOut_ = Half::None;
    return {};
  }

  // Releases the half returned by the last getReadyHalf().
  void release() {
    switch (handedOut_) {
    case Half::Lower:
      lowerReady_ = false;
      break;
    case Half::Upper:
      upperReady_ = false;
      break;
    case Half::None:
      break;
    }
    handedOut_ = Half::None;
  }

  // Total since startup; wraps at 0xFFFF.
  std::uint16_t overrunCount() const { return overrun_; }

private:
  enum class Half { Lower, Upper, None };

  // Written by the DMA, which the compiler can't see; volatile forces real
  // reads.
  std::array<volatile std::uint16_t, N> buffer_{};
  // Shared with the DMA ISR.
  volatile bool lowerReady_{};
  volatile bool upperReady_{};
  volatile std::uint16_t overrun_{};
  // Main loop only.
  Half handedOut_{Half::None};
};
