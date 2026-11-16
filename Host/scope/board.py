"""Board facts: constants that mirror the firmware's configuration.

Change these together with the firmware, never on their own.
"""

# USB vendor ID of the ST-LINK, whose virtual COM port carries the stream.
VID = 0x0483

# Baud rate of the firmware's UART.
BAUDRATE = 115200

# Samples per second: the rate of the timer that triggers the ADC.
SAMPLE_RATE = 1000.0

# Largest sample value: the ADC samples with 12 bits.
ADC_MAX = 4095
