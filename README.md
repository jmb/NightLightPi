# Night Light Pi - An MQTT enabled, temperature sensing night light for the Raspberry Pi

This project was created in order to replicate commercially available night light products which change colour based on the temperature, but with the added functionality of being able to report the sensor data to remote locations. The lightweight MQTT protocol has been used to achieve this aim along with APA102 neopixels which can easily be run from a Raspberry Pi.

## Hardware

In my setup I use the following:
* Raspberry Pi Zero with USB Wifi Dongle (you could just use a Raspberry Pi Zero W)
* Strip of 10 APA102 RGB LEDs
* DHT22 or AM2302 Temperature and Humidity sensor
* SSD1306 OLED Display
* 74AHCT125 or 74AHC125 level shifter
* 2 momentary push to make buttons

I have also used a ProtoZero board to keep all the soldering and connections neat.

The pin outs on the Raspberry Pi GPIO are as follows:
* The APA102 strip is connected to the Raspberry Pi via the level shifter as per the instructions in the [APA102_Pi](https://github.com/tinue/APA102_Pi) library (pins 10 (MOSI) and 11 (SCLK)). Power-wise I calculated that with only 10 LEDs there would be enough available to power the strip, but this needs checking for your setup - [this page from Adafruit is useful](https://learn.adafruit.com/adafruit-neopixel-uberguide/power).
* The DHT22 data pin is connected to Pi pin 22.
* The OLED is connected with SDA to Pi pin 2 and SCL to Pi pin 3.
* The two buttons use pins 23 and 24 with their other side connected to GND.


## License

Distributed under the MIT license. See [LICENSE](LICENSE) for more information.

## Contributing

1. Fork it (<https://github.com/jmb/NightLightPi/fork>)
2. Create your feature branch (`git checkout -b feature/fooBar`)
3. Commit your changes (`git commit -am 'Add some fooBar'`)
4. Push to the branch (`git push origin feature/fooBar`)
5. Create a new Pull Request
