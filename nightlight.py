#!/usr/bin/python3
import Adafruit_DHT
import apa102
import Adafruit_SSD1306
import paho.mqtt.client as mqtt
import time
import RPi.GPIO as GPIO
import threading
import logging

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


# Set logging level
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


class NightLight(threading.Thread):
   config = {}

   # Temperature Sensor Settings
   config['TemperatureSensor'] = { 'type': Adafruit_DHT.AM2302,
                                   'pin': 22,
                                   'updateSeconds': 60, # every x seconds
                                   }

   # MQTT Settings
   config['MQTT'] = {  'enable': True,
                       'server': 'SERVER',
                       'port': 8883,
                       'user': 'USERNAME',
                       'password': 'PASSWORD',
                       'temperatureTopic': "nightlight/temperature",
                       'humidityTopic': "nightlight/humidity",
                       'displayTopic': "nightlight/display",
                       'lightTopic': "nightlight/light",
                       'brightnessTopic': "nightlight/brightness",

                       }

   # LED Strip Settings
   config['LEDStrip'] = {  'length': 10,
                           'light': 10,
                           'maxBrightness': 30,
                           'brightness': 6
                           }

   # Input buttons
   config['Buttons'] = {   'Light': 23,
                           'Display': 24,
                           }
   config['TemperatureSensor']['ranges'] = (16,20,23.9)
   config['TemperatureSensor']['colours'] = ( (20, 0, 255), (255, 200, 10), (255, 128, 0), (255, 0, 0) )

   config['Modes'] = {     'Off': {'menu': 'menu_off.ppm'},
                           'Temperature': {'menu': 'menu_temperature.ppm',
                                           'background': 'temperature.ppm',
                                           },
                           'Rainbow': {'menu': 'menu_rainbow.ppm'},
                           }

   config['LightModeOrder'] = ['Temperature', 'Rainbow', 'Off']


   config['Speed'] = 1 # 1 second delay

   menu_button_pressed_time = 0
   menu_displayed = 0


   def __init__(self):
       super().__init__()
       self.temperature = None
       self.humidity = None

       self.mode = 'Run'

       self.displayMode = 'Temperature'
       self.lightMode = 0
       self.rainbow_colour = 0

       def on_mqtt_connect(client, userdata, rc):
           logging.info("MQTT Connection returned result: "+mqtt.connack_string(rc))

           # Subscribing in on_connect() means that if we lose the connection and
         # reconnect then subscriptions will be renewed.
           self.mqttc.subscribe(self.config['MQTT']['displayTopic'] + '/set')
           self.mqttc.subscribe(self.config['MQTT']['lightTopic'] + '/set')
           self.mqttc.subscribe(self.config['MQTT']['brightnessTopic'] + '/set')


       def on_mqtt_disconnect(client, userdata, rc):
           if rc != 0:
               logging.warning("Unexpected MQTT disconnection.")

       # Setup MQTT
       mqttConfig = self.config['MQTT']
       if mqttConfig['enable']:
           self.mqttc = mqtt.Client(client_id=mqttConfig['user'])
           self.mqttc.tls_set("/etc/ssl/certs/DST_Root_CA_X3.pem")
           self.mqttc.username_pw_set(mqttConfig['user'], password=mqttConfig['password'])

           self.mqttc.on_connect = on_mqtt_connect
           self.mqttc.on_disconnect = on_mqtt_disconnect
           self.mqttc.on_message = self.on_mqtt_message

           self.mqttc.connect(mqttConfig['server'], port=mqttConfig['port'])
           self.mqttc.loop_start()




       # Setup LED Strip
       ledConfig = self.config['LEDStrip']
       self.LEDStrip = apa102.APA102(numLEDs=ledConfig['length'], globalBrightness=ledConfig['maxBrightness'], order='rgb')
       self.LEDStrip_lock = threading.Lock()

       self.setLightMode(self.lightMode)

       # OLED Display Settings - 128x64 display with hardware I2C:
       self.display = Adafruit_SSD1306.SSD1306_128_64(rst=0)
       self.display.begin()
       self.display.clear()
       self.display.display()
       self.display_lock = threading.Lock()

       #self.setDisplayMode(self.displayMode)

       # Setup buttons
       GPIO.setmode(GPIO.BCM)
       menu_button_pin = self.config['Buttons']['Light']
       GPIO.setup(menu_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
       GPIO.add_event_detect(menu_button_pin, GPIO.FALLING, callback=self.lightButtonPressed, bouncetime=500)
       timer_button_pin = self.config['Buttons']['Display']
       GPIO.setup(timer_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
       GPIO.add_event_detect(timer_button_pin, GPIO.FALLING, callback=self.displayButtonPressed, bouncetime=500)



   def publishData(self, temperature, humidity):
       mqttConfig = self.config['MQTT']
       if mqttConfig['enable']:
           self.mqttc.publish(mqttConfig['temperatureTopic'], payload="{:0.1f}".format(temperature), retain=True)
           self.mqttc.publish(mqttConfig['humidityTopic'], payload="{:0.1f}".format(humidity), retain=True)


   # Set the entire strip to the same colour
   def setStripRGB(self, rgb):
       ledConfig = self.config['LEDStrip']
       strip = self.LEDStrip
       self.LEDStrip_lock.acquire()
       brightness = ledConfig['brightness']
       if ledConfig['light'] > 0: # Light LEDs from the start of the strip
           for pixel in range(ledConfig['light']):
               strip.setPixelRGB(pixel, rgb, brightness)
       elif ledConfig['light'] < 0: # Light LEDs from the end of the strip
           for pixel in list(range(ledConfig['length']))[ledConfig['light']:ledConfig['length']]:
               strip.setPixelRGB(pixel, rgb, brightness)
       strip.show()
       self.LEDStrip_lock.release()


   # Set the entire strip to the same colour
   def setStrip(self, rgb_tuple):
       colour = self.LEDStrip.combineColor(rgb_tuple[0], rgb_tuple[1], rgb_tuple[2])
       self.stripColour = colour
       self.setStripRGB(colour)


   def displayImage(self, image):
       self.display_lock.acquire()
       self.display.image(image)
       self.display.display()
       self.display_lock.release()


   def displayTemperature(self):
       if self.displayMode == 'Off':
           return

       if self.temperature is None:
           self.displayTemperatureMenu()
           return

       temperature = self.temperature
       humidity = self.humidity



       # Set the OLED display to show temperature
       display = self.display
       padding = 2
       padding_x = 38
       width = display.width
       height = display.height

       image = Image.open(self.config['Modes']['Temperature']['background']).convert('1')
       draw = ImageDraw.Draw(image)

       font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30)
       font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
       temperature_string = "{0:0.1f}Â°".format(temperature)  # â„ƒ

       temperature_size = draw.textsize(temperature_string, font=font)
       x = ((width - padding_x) - temperature_size[0])/2 + padding_x
       draw.text((x, padding), temperature_string, font=font, fill=255)

       humidity_string = "{0:0.1f}%".format(humidity)
       humidity_size = draw.textsize(humidity_string, font=font_small)
       x = ((width - padding_x) - humidity_size[0])/2 + padding_x
       y = (height - padding) - humidity_size[1]
       draw.text((x,y), humidity_string, font=font_small, fill=255)

       self.displayImage(image)

   def displayOff(self):
       display = self.display

       self.display_lock.acquire()
       display.clear()
       display.display()
       self.display_lock.release()


   def displayTemperatureMenu(self):
       image = Image.open(self.config['Modes']['Temperature']['menu']).convert('1')
       self.displayImage(image)


   def lightTemperature(self):
       if self.temperature is None:
           self.setStripRGB(self.LEDStrip.wheel(140))
           return

       temperature = self.temperature
       # Set the LED strip to the correct colour
       temperature_ranges = self.config['TemperatureSensor']['ranges']
       temperature_colours = self.config['TemperatureSensor']['colours']
       if temperature <= temperature_ranges[0]:
           self.setStrip(temperature_colours[0])
       elif temperature >= temperature_ranges[-1]:
           self.setStrip(temperature_colours[-1])
       else:
           for range_boundary in range(len(temperature_ranges) - 1 ):
               if (temperature > temperature_ranges[range_boundary]) and (temperature <= temperature_ranges[range_boundary+1]):
                   self.setStrip(temperature_colours[range_boundary+1])

   def lightQuickRainbow(self):
       rainbow_colour = 0
       while rainbow_colour < 255:
           self.setStripRGB(self.LEDStrip.wheel(rainbow_colour))
           rainbow_colour = rainbow_colour + 1
           #time.sleep(0.01)

       self.setStripRGB(self.LEDStrip.wheel(0))

   def lightOff(self):
       self.LEDStrip_lock.acquire()
       self.LEDStrip.clearStrip()
       self.LEDStrip.show()
       self.LEDStrip_lock.release()


   def turnOff(self):
       self.displayOff()
       self.lightOff()

   def stop(self):
       self.mode = 'Stop'
       self.turnOff()
       self.LEDStrip.cleanup()
       self.mqttc.loop_stop()
       self.mqttc.disconnect()
       GPIO.cleanup()

   def __del__(self):
       self.stop()

   def on_mqtt_message(self, client, userdata, message):
       topic = message.topic #.decode('utf-8')
       payload = message.payload.decode('utf-8')

       logging.info("Received MQTT message with topic {} : {}".format(topic, payload))

       if topic == self.config['MQTT']['displayTopic'] + '/set':
           self.setDisplayMode(payload)

       elif topic == self.config['MQTT']['lightTopic'] + '/set':
           for index, mode in enumerate(self.config['LightModeOrder']):
               if payload == mode:
                   self.setLightMode(index)

       elif topic == self.config['MQTT']['brightnessTopic'] + '/set':
           self.setBrightness(payload)


   def setBrightness(self, brightness):
       current_brightness = self.config['LEDStrip']['brightness']
       try:
           new_brightness = int(brightness)
           self.config['LEDStrip']['brightness'] = new_brightness

           # Update immediately if in temp mode otherwise could take up to a minute
           if self.config['LightModeOrder'][self.lightMode] == 'Temperature':
               self.lightTemperature()

           mqttConfig = self.config['MQTT']
           if mqttConfig['enable']:
               self.mqttc.publish(mqttConfig['brightnessTopic'], new_brightness, retain=True)

           status = 'Brightness: {0}'.format(new_brightness)
           logging.info(status)

       except:
           logging.warning("Could not set brightness to '{}', leaving at {}".format(brightness, current_brightness))


   # Toggles Display on and off
   def displayButtonPressed(self, *args):
       logging.info("Display button pressed")
       if self.displayMode == 'Temperature':
           self.setDisplayMode('Off')
       elif self.displayMode == 'Off':
           self.setDisplayMode('Temperature')


   def setDisplayMode(self, mode):
       self.displayMode = mode
       if self.displayMode == 'Temperature':
           self.displayTemperature()
       elif self.displayMode == 'Off':
           self.displayOff()

       mqttConfig = self.config['MQTT']
       if mqttConfig['enable']:
           self.mqttc.publish(mqttConfig['displayTopic'], self.displayMode, retain=True)

       status = 'Display Mode: {0}'.format(self.displayMode)
       logging.info(status)


   def lightButtonPressed(self, *args):
       logging.info("Light button pressed")
       new_mode = (self.lightMode + 1) % len(self.config['LightModeOrder'])
       #self.lightMode = new_mode % len(self.config['LightModeOrder'])

       mode_text = self.config['LightModeOrder'][new_mode]
       if mode_text == 'Rainbow':
           self.lightQuickRainbow()

       self.setLightMode(new_mode)



   def setLightMode(self, mode):
       mode_text = self.config['LightModeOrder'][mode]
       self.lightMode = mode

       if mode_text == 'Off':
           self.lightOff()

       elif mode_text == 'Temperature':
           self.lightTemperature()

       mqttConfig = self.config['MQTT']
       if mqttConfig['enable']:
           self.mqttc.publish(mqttConfig['lightTopic'], mode_text, retain=True)

       status = 'Light Mode: {0}'.format(self.config['LightModeOrder'][self.lightMode])
       logging.info(status)



   def getData(self):
       # Try to grab a sensor reading and publish it.  Use the read_retry method which will retry up
       # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
       sensorConfig = self.config['TemperatureSensor']
       humidity, temperature = Adafruit_DHT.read_retry(sensorConfig['type'], sensorConfig['pin'])

       if humidity is not None and temperature is not None:
           self.humidity = humidity
           self.temperature = temperature

           status = 'Temp={0:0.1f}Â°C  Humidity={1:0.1f}%'.format(temperature, humidity)
           logging.info(status)

           self.publishData(temperature, humidity)

       if self.displayMode == 'Temperature':
           self.displayTemperature()

       if self.config['LightModeOrder'][self.lightMode] == 'Temperature':
           self.lightTemperature()


   def run(self):
       last_update = 0
       last_rainbow = 0

       # Set display and light immediately on start up...
       self.displayTemperatureMenu()
       #self.setStripRGB(self.LEDStrip.wheel(170))


       # Start a thread to get temperature
       sensor = threading.Timer(0, self.getData)
       sensor.start()

       while self.mode != 'Stop':
           now = time.time()

           if not sensor.is_alive():
               sensor = threading.Timer(self.config['TemperatureSensor']['updateSeconds'], self.getData)
               sensor.start()

           if self.config['LightModeOrder'][self.lightMode] == 'Rainbow':
               if (now - last_rainbow) > self.config['Speed']:
                   self.setStripRGB(self.LEDStrip.wheel(self.rainbow_colour))
                   self.rainbow_colour = (self.rainbow_colour + 1) % 255
                   last_rainbow = now

       sensor.cancel()



if __name__ == '__main__':
   t = NightLight()
   t.daemon = True
   t.start()

   try:
       t.join()
   except (KeyboardInterrupt, SystemExit):
       logging.warning("NightLight Stopping.")
       t.stop()