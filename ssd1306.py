# -*-coding:utf-8 -*-
"""
Created on 2016-5-29

@author: Danny
DannyWork Project
"""

from __future__ import division

import time

import Adafruit_GPIO as GPIO
import Adafruit_GPIO.SPI as SPI


# Constants
from chars import F6_8_CHARS, F8_16_CHARS

SSD1306_I2C_ADDRESS = 0x3C    # 011110+SA0+RW - 0x3C or 0x3D
SSD1306_SETCONTRAST = 0x81
SSD1306_DISPLAYALLON_RESUME = 0xA4
SSD1306_DISPLAYALLON = 0xA5
SSD1306_NORMALDISPLAY = 0xA6
SSD1306_INVERTDISPLAY = 0xA7
SSD1306_DISPLAYOFF = 0xAE
SSD1306_DISPLAYON = 0xAF
SSD1306_SETDISPLAYOFFSET = 0xD3
SSD1306_SETCOMPINS = 0xDA
SSD1306_SETVCOMDETECT = 0xDB
SSD1306_SETDISPLAYCLOCKDIV = 0xD5
SSD1306_SETPRECHARGE = 0xD9
SSD1306_SETMULTIPLEX = 0xA8
SSD1306_SETLOWCOLUMN = 0x00
SSD1306_SETHIGHCOLUMN = 0x10
SSD1306_SETSTARTLINE = 0x40
SSD1306_MEMORYMODE = 0x20
SSD1306_COLUMNADDR = 0x21
SSD1306_PAGEADDR = 0x22
SSD1306_COMSCANINC = 0xC0
SSD1306_COMSCANDEC = 0xC8
SSD1306_SEGREMAP = 0xA0
SSD1306_CHARGEPUMP = 0x8D
SSD1306_EXTERNALVCC = 0x1
SSD1306_SWITCHCAPVCC = 0x2

# Scrolling constants
SSD1306_ACTIVATE_SCROLL = 0x2F
SSD1306_DEACTIVATE_SCROLL = 0x2E
SSD1306_SET_VERTICAL_SCROLL_AREA = 0xA3
SSD1306_RIGHT_HORIZONTAL_SCROLL = 0x26
SSD1306_LEFT_HORIZONTAL_SCROLL = 0x27
SSD1306_VERTICAL_AND_RIGHT_HORIZONTAL_SCROLL = 0x29
SSD1306_VERTICAL_AND_LEFT_HORIZONTAL_SCROLL = 0x2A


class SSD1306Base(object):
    """
    Base class for SSD1306-based OLED displays.
    Implementors should subclass and provide an implementation for the _initialize function.
    """

    def __init__(self, width, height, rst, dc=None, sclk=None, din=None, cs=None, gpio=None,
                 spi=None, i2c_bus=None, i2c_address=SSD1306_I2C_ADDRESS,
                 i2c=None):
        self._spi = None
        self._i2c = None
        self.width = width
        self.height = height
        self._pages = height // 8
        self._buffer = [0] * width * self._pages
        self._cursor = 0

        # Default to platform GPIO if not provided.
        self._gpio = gpio
        if self._gpio is None:
            self._gpio = GPIO.get_platform_gpio()

        # Setup reset pin.
        self._rst = rst
        self._gpio.setup(self._rst, GPIO.OUT)

        # Handle hardware SPI
        if spi is not None:
            self._spi = spi
            self._spi.set_clock_hz(8000000)
        # Handle software SPI
        elif sclk is not None and din is not None and cs is not None:
            self._spi = SPI.BitBang(self._gpio, sclk, din, None, cs)
        # Handle hardware I2C
        elif i2c is not None:
            self._i2c = i2c.get_i2c_device(i2c_address)
        else:
            import Adafruit_GPIO.I2C as I2C

            self._i2c = I2C.get_i2c_device(i2c_address) if i2c_bus is None else I2C.get_i2c_device(i2c_address,
                                                                                                   busnum=i2c_bus)

        # Initialize DC pin if using SPI.
        if self._spi is not None:
            if dc is None:
                raise ValueError('DC pin must be provided when using SPI.')
            self._dc = dc
            self._gpio.setup(self._dc, GPIO.OUT)

    def _initialize(self):
        raise NotImplementedError

    def command(self, c):
        """
        Send command byte to display.
        """

        if self._spi is not None:
            # SPI write.
            self._gpio.set_low(self._dc)
            self._spi.write([c])
        else:
            # I2C write.
            control = 0x00   # Co = 0, DC = 0
            self._i2c.write8(control, c)

    def data(self, c):
        """
        Send byte of data to display.
        """

        if self._spi is not None:
            # SPI write.
            self._gpio.set_high(self._dc)
            self._spi.write([c])
        else:
            # I2C write.
            control = 0x40   # Co = 0, DC = 0
            self._i2c.write8(control, c)

    def begin(self, vccstate=SSD1306_SWITCHCAPVCC):
        """
        Initialize display.
        """

        # Save vcc state.
        self._vccstate = vccstate

        # Reset and initialize display.
        self.reset()
        self._initialize()

        # Turn on the display.
        self.command(SSD1306_DISPLAYON)

    def reset(self):
        """
        Reset the display.
        """

        # Set reset high for a millisecond.
        self._gpio.set_high(self._rst)
        time.sleep(0.001)

        # Set reset low for 10 milliseconds.
        self._gpio.set_low(self._rst)
        time.sleep(0.010)

        # Set reset high again.
        self._gpio.set_high(self._rst)

    def display(self):
        """
        Write display buffer to physical display.
        """

        self.command(SSD1306_COLUMNADDR)
        self.command(0)              # Column start address. (0 = reset)
        self.command(self.width-1)   # Column end address.
        self.command(SSD1306_PAGEADDR)
        self.command(0)              # Page start address. (0 = reset)
        self.command(self._pages-1)  # Page end address.

        # Write buffer data.
        if self._spi is not None:
            # Set DC high for data.
            self._gpio.set_high(self._dc)
            # Write buffer.
            self._spi.write(self._buffer)
        else:
            for i in range(0, len(self._buffer), 16):
                control = 0x40   # Co = 0, DC = 0
                self._i2c.writeList(control, self._buffer[i:i+16])

    def image(self, image):
        """
        Set buffer to value of Python Imaging Library image.  The image should
        be in 1 bit mode and a size equal to the display size.
        """

        if image.mode != '1':
            raise ValueError('Image must be in mode 1.')

        imwidth, imheight = image.size
        if imwidth != self.width or imheight != self.height:
            raise ValueError('Image must be same dimensions as display ({0}x{1}).'.format(self.width, self.height))

        # Grab all the pixels from the image, faster than getpixel.
        pix = image.load()
        # Iterate through the memory pages
        index = 0
        for page in range(self._pages):
            # Iterate through all x axis columns.
            for x in range(self.width):
                # Set the bits for the column of pixels at the current position.
                bits = 0
                # Don't use range here as it's a bit slow
                for bit in [0, 1, 2, 3, 4, 5, 6, 7]:
                    bits <<= 1
                    bits |= 0 if pix[(x, page*8+7-bit)] == 0 else 1
                # Update buffer byte and increment to next byte.
                self._buffer[index] = bits
                index += 1

    def clear(self):
        """
        Clear contents of image buffer.
        """

        self._buffer = [0]*(self.width*self._pages)

    def set_contrast(self, contrast):
        """
        Sets the contrast of the display.  Contrast should be a value between 0 and 255.
        """

        if contrast < 0 or contrast > 255:
            raise ValueError('Contrast must be a value from 0 to 255 (inclusive).')
        self.command(SSD1306_SETCONTRAST)
        self.command(contrast)

    def dim(self, dim):
        """
        Adjusts contrast to dim the display if dim is True, otherwise sets the
        contrast to normal brightness if dim is False.
        """

        # Assume dim display.
        contrast = 0
        # Adjust contrast based on VCC if not dimming.

        if not dim:
            if self._vccstate == SSD1306_EXTERNALVCC:
                contrast = 0x9F
            else:
                contrast = 0xCF

    def set_char(self, c, size='6_8', location=0):
        if c == '\n':
            self.break_line()
        if location > len(self._buffer):
            return

        if size == '6_8' and F6_8_CHARS.get(c):
            buff = F6_8_CHARS.get(c)
            self._buffer[location:location + len(buff)] = buff
        elif size == '8_16' and F8_16_CHARS.get(c):
            buff = F8_16_CHARS.get(c)
            mid = len(buff) // 2
            self._buffer[location:location + mid] = buff[:mid]
            self._buffer[location + 128:location + mid + 128] = buff[mid:]

    def set_chars(self, cs, size='6_8', location=0):
        line = location // 128

        spacing = {
            '6_8': 6,
            '8_16': 8
        }.get(size)
        for c in cs:
            self.set_char(c, size, location)
            location += spacing
            if location // 128 > line and size == '8_16':
                location += 128
                line += 2

    def set_line(self, t, size='6_8', align='left', location=0):
        spacing = {
            '6_8': 6,
            '8_16': 8
        }.get(size)
        l = (128 - location % 128) // spacing
        if align == 'left':
            t = t.ljust(l)
        elif align == 'right':
            t = t.rjust(l)
        else:
            t = t.center(l)
        self.set_chars(t, size, location)

    def break_line(self):
        self._cursor += 128 - self._cursor % 128


class SSD1306_128_64(SSD1306Base):
    def __init__(self, rst, dc=None, sclk=None, din=None, cs=None, gpio=None, spi=None,
                 i2c_bus=None, i2c_address=SSD1306_I2C_ADDRESS, i2c=None):

        # Call base class constructor.
        super(SSD1306_128_64, self).__init__(128, 64, rst, dc, sclk, din, cs,
                                             gpio, spi, i2c_bus, i2c_address, i2c)

    def _initialize(self):
        # 128x64 pixel specific initialization.
        self.command(SSD1306_DISPLAYOFF)                    # 0xAE
        self.command(SSD1306_SETDISPLAYCLOCKDIV)            # 0xD5
        self.command(0x80)                                  # the suggested ratio 0x80
        self.command(SSD1306_SETMULTIPLEX)                  # 0xA8
        self.command(0x3F)
        self.command(SSD1306_SETDISPLAYOFFSET)              # 0xD3
        self.command(0x0)                                   # no offset
        self.command(SSD1306_SETSTARTLINE | 0x0)            # line #0
        self.command(SSD1306_CHARGEPUMP)                    # 0x8D
        if self._vccstate == SSD1306_EXTERNALVCC:
            self.command(0x10)
        else:
            self.command(0x14)
        self.command(SSD1306_MEMORYMODE)                    # 0x20
        self.command(0x00)                                  # 0x0 act like ks0108
        self.command(SSD1306_SEGREMAP | 0x1)
        self.command(SSD1306_COMSCANDEC)
        self.command(SSD1306_SETCOMPINS)                    # 0xDA
        self.command(0x12)
        self.command(SSD1306_SETCONTRAST)                   # 0x81
        if self._vccstate == SSD1306_EXTERNALVCC:
            self.command(0x9F)
        else:
            self.command(0xCF)
        self.command(SSD1306_SETPRECHARGE)                  # 0xd9
        if self._vccstate == SSD1306_EXTERNALVCC:
            self.command(0x22)
        else:
            self.command(0xF1)
        self.command(SSD1306_SETVCOMDETECT)                 # 0xDB
        self.command(0x40)
        self.command(SSD1306_DISPLAYALLON_RESUME)           # 0xA4
        self.command(SSD1306_NORMALDISPLAY)                 # 0xA6
