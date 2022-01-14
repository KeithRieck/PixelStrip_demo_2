import utime
import pixelstrip
from random import randint
from math import sin, floor, ceil
from machine import Pin

PIN = 4
NUM_PIXELS = 144
BRIGHTNESS = 0.8

blendSelf = 2
blendNeighbor1 = 3
blendNeighbor2 = 2
blendNeighbor3 = 1
blendTotal = (blendSelf + blendNeighbor1 + blendNeighbor2 + blendNeighbor3)


class FireAnimation(pixelstrip.Animation):
    """
    See https://github.com/davepl/DavesGarageLEDSeries/blob/master/LED%20Episode%2010/include/fire.h
    """
    def __init__(self, cooling=60, sparking=50, sparks=3, sparkHeight=4):
        pixelstrip.Animation.__init__(self)
        self.cooling = cooling
        self.sparking = sparking
        self.sparks = sparks
        self.sparkHeight = sparkHeight

    def reset(self, strip):
        self.heat = [0] * strip.n
        strip.clear()

    def draw(self, strip, delta_time):
        size = strip.n
        
        # First cool each cell by a little bit
        coolRange = floor(((self.cooling * 10) / size) + 2)
        for p in range(size):
            self.heat[p] = max(0, floor(self.heat[p] - randint(0, coolRange)))
            
        # Next drift heat up and diffuse it a little bit
        for p in range(3, size):
            self.heat[p] = floor((self.heat[p] * blendSelf + 
                       self.heat[(p - 1) % strip.n] * blendNeighbor1 + 
                       self.heat[(p - 2) % strip.n] * blendNeighbor2 + 
                       self.heat[(p - 3) % strip.n] * blendNeighbor3) / blendTotal) % 256

        # Randomly ignite new sparks down in the flame kernel
        for _ in range(self.sparks):
            if randint(0, 255) < self.sparking:
                p = randint(0, self.sparkHeight)
                self.heat[p] = (self.heat[p] + randint(160, 255)) % 256

        for p in range(size):
            strip[p] = heatColor(self.heat[p])

        strip.show()
        
def heatColor(temperature):
    "Translate a temperature number (0-255) into a color representing its heat"
    t192 = scale8_video(temperature, 192)
    heatramp = (t192 & 0x3F) << 2
    if t192 & 0x80:
        return (0xFF, 0xFF, heatramp, 0x00)
    elif t192 & 0x40:
        return (0xFF, heatramp, 0x00, 0x00)
    else:
        return (heatramp, 0x00, 0x00, 0x00)
    
def scale8_video(i, sc):
    return floor((i * sc) / 256)

def blink(n, strip=None):
    "Blink lights to show that the program has loaded successfully"
    led = Pin(25, Pin.OUT)
    if strip:
        strip.clear()
    for _ in range(n):
        led.toggle()
        if strip:
            strip[0] = (0, 128, 0, 0)
            strip.show()
        utime.sleep(0.3)
        led.toggle()
        if strip:
            strip.clear()
            strip.show()
        utime.sleep(0.3)

class SpinningAnimation(pixelstrip.Animation):
    """
    One colored pixel travels across the strip.
    """
    def __init__(self, color, cycle_time=1.0, name=None):
        pixelstrip.Animation.__init__(self, name)
        self.color = color
        self.current_pixel = 0
        self.cycle_time = cycle_time
        self.wait_time = self.cycle_time / 8

    def reset(self, strip):
        self.current_pixel = 0
        self.wait_time = self.cycle_time / strip.n
        self.timeout = self.wait_time

    def draw(self, strip, delta_time):
        if self.is_timed_out():
            self.timeout = self.wait_time
            self.current_pixel = (self.current_pixel + 1) % strip.n
            strip.clear()
            strip[self.current_pixel] = self.color
            strip.show()

class RippleAnimation(pixelstrip.Animation):
    """
    Pixels fade in and out of color, based on the sum of sine curves.
    """
    def __init__(
        self,
        color_list=[(0, 0, 0, 0), (255, 0, 0, 0), (128, 128, 0, 0), (0, 0, 0, 0)],
        curve_list=[(0.125, 1.0, 1.0), (0.156, 0.8, 0.9), (0.100, 1.1, 1.1)],
        cycle_time=40.0,
        x_span=100,
        name=None
    ):
        pixelstrip.Animation.__init__(self, name)
        self.color_list = color_list
        self.cycle_time = cycle_time
        self.x_span = x_span
        self.curve_list = curve_list

    def reset(self, strip):
        strip.clear()
        strip.show()

    def draw(self, strip, delta_time):
        m = pixelstrip.current_time() * 1000.0
        for p in range(strip.n):
            c = 0.0
            for curve in self.curve_list:
                c = c + self.g(p, m, curve[0], curve[1], curve[2])
            c = c / len(self.curve_list)
            c = min(max(c, 0.0), 1.0)
            strip[p] = self.shift_color(c)
        strip.show()

    def f(self, x, t, w):
        return sin(t + 6.28 * x / (w * 2 * self.x_span))

    def g(self, x, m, w, a, d):
        s = d * self.cycle_time
        t0 = ((m % (s * 2)) - s) / s
        t = 6.28 * sin(6.28 * t0)
        return self.f(x, t, w) * a

    def shift_color(self, c):
        color_list_size = len(self.color_list) - 1
        color_num_0 = floor(c * color_list_size)
        color_num_1 = ceil(c * color_list_size)
        c0 = (c - color_num_0 / color_list_size) * color_list_size
        c1 = 1.0 - c0
        return (
            floor(c0 * self.color_list[color_num_0][0] + c1 * self.color_list[color_num_1][0]),
            floor(c0 * self.color_list[color_num_0][1] + c1 * self.color_list[color_num_1][1]),
            floor(c0 * self.color_list[color_num_0][2] + c1 * self.color_list[color_num_1][2]),
            floor(c0 * self.color_list[color_num_0][3] + c1 * self.color_list[color_num_1][3])
        )


def main():
    strip1 = pixelstrip.PixelStrip(PIN, NUM_PIXELS)
    strip1.brightness = BRIGHTNESS
    strip1.animation = FireAnimation(cooling=70, sparking=30)
    # strip1.animation = RippleAnimation()
    strip2 = pixelstrip.PixelStrip(5, 8)
    strip2.brightness = BRIGHTNESS
    strip2.animation = SpinningAnimation(color=(128, 0, 0, 0))
    strip3 = pixelstrip.PixelStrip(8, 8)
    strip3.brightness = BRIGHTNESS
    strip3.animation = SpinningAnimation(color=(0, 128, 0, 0))
    strip4 = pixelstrip.PixelStrip(9, 8)
    strip4.brightness = BRIGHTNESS
    strip4.animation = SpinningAnimation(color=(0, 0, 128, 0))
    blink(3, strip=strip1)
    while True:
        strip1.draw()
        strip2.draw()
        strip3.draw()
        strip4.draw()
        utime.sleep(0.02)
        
main()





