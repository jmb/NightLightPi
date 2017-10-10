# -*- coding: utf-8; -*-
"""Handle configuration file loading and fallback behaviors.

This module exports the load_config method which will attempt to load
application configuration from disk. It will first check to see if an
environment variable has been set to indicate the path of the config
file. If the environment variable is not set, it will assume the user
is running on a Raspberry PI using Linux and will attempt to find the
configuration file at /etc/nightlightpi/nightlightpi.yaml.

Example:
    conf = load_config()
    if conf.some_value:
        print("some_value was set in the config!")

"""

__all__ = ["load_config"]

from os import environ
from os.path import join

from pkg_resources import resource_filename
from pykwalify.core import Core
from pykwalify.errors import SchemaError
from yaml import safe_load

from nightlightpi.errorstrings import MISSING_CONFIG_VALUE


ETCPATH = join("/", "etc", "nightlightpi", "nightlightpi.yaml")
ENVCONFIGPATH = "NIGHTLIGHTPICONFIG"


def load_config():
    """Load configuration from disk, returned as a Config instance."""
    data = load_valid_yaml(environ.get(ENVCONFIGPATH, ETCPATH))
    conf = Config()
    try:
        _set_config_values(conf, data)
    except KeyError as e:
        raise RuntimeError(MISSING_CONFIG_VALUE.format(e.args[0]))
    return conf


def load_valid_yaml(path):
    """Return a dict deserialized from the file located at path.
The data will be validated against the schema defined in conf-schema.yaml.

    """
    schema_path = resource_filename("nightlightpi", "conf-schema.yaml")
    c = Core(source_file=path, schema_files=[schema_path])
    return c.validate()


# TODO: This could be simplified by using YAML SafeLoader and using object
# deserialization. (wkmanire 2017-10-10)

def _set_config_values(conf, data):
    """Copy data from the YAML configuration data into the Config instance."""
    _set_mqtt_values(conf.mqtt, data)
    _set_led_strip_values(conf.led_strip, data)
    _set_inputs_values(conf.inputs, data)
    _set_temperature_values(conf.temperature, data)
    _set_display_mode_values(conf.off_mode, "Off", data)
    _set_display_mode_values(conf.temp_mode, "Temperature", data)
    _set_display_mode_values(conf.rainbow_mode, "Rainbow", data)


def _set_mqtt_values(mqtt, data):
    mqtt_data = data["mqtt"]
    mqtt.brightness_topic = mqtt_data["brightness_topic"]
    mqtt.display_topic = mqtt_data["display_topic"]
    mqtt.enable = mqtt_data["enable"]
    mqtt.humidity_topic = mqtt_data["humidity_topic"]
    mqtt.light_topic = mqtt_data["light_topic"]
    mqtt.password = mqtt_data["password"]
    mqtt.port = mqtt_data["port"]
    mqtt.server = mqtt_data["server"]
    mqtt.temperature_topic = mqtt_data["temperature_topic"]
    mqtt.user = mqtt_data["user"]


def _set_led_strip_values(led_strip, data):
    led_strip_data = data["led_strip"]
    led_strip.length = led_strip_data["length"]
    led_strip.light = led_strip_data["light"]
    led_strip.max_brightness = led_strip_data["max_brightness"]
    led_strip.brightness = led_strip_data["brightness"]


def _set_inputs_values(inputs, data):
    inputs_data = data["inputs"]
    inputs.length = inputs_data["buttons_light"]
    inputs.buttons_display = inputs_data["buttons_display"]


def _set_temperature_values(temp_config, data):
    temp_config_data = data["temperature"]
    temp_config.sensor_ranges = temp_config_data["sensor_ranges"]
    colours = list()
    for c in temp_config_data["sensor_colours"]:
        colours.append((c["r"], c["g"], c["b"]))
    temp_config.sensor_colours = colours


def _set_time_values(timing_config, data):
    timing_data = data["timing"]
    timing_config.speed_in_seconds = timing_data["speed_in_seconds"]
    timing_config.menu_button_pressed_time_in_seconds = timing_data["menu_button_pressed_time_in_seconds"]
    timing_config.menu_display = timing_data["menu_display"]


def _set_display_mode_values(mode, name, data):
    for mode_data in data["display_modes"]:
        if mode_data["name"] == name:
            mode.name = mode_data["name"]
            mode.menu = mode_data["menu"]
            mode.background = mode_data["background"]


class Config:
    """Provide configuration for the MQTT server and RPi attached device.
This is a composite configuration class built up from other
configuration objects.

    """

    def __init__(self):
        self.mqtt = MQTTConfig()
        self.led_strip = LEDStripConfig()
        self.inputs = InputsConfig()
        self.temperature = TemperatureConfig()
        self.timing = TimingConfig()
        self.off_mode = DisplayModeConfig()
        self.temp_mode = DisplayModeConfig()
        self.rainbow_mode = DisplayModeConfig()


class MQTTConfig:

    def __init__(self):
        self.enable = None
        self.server = None
        self.port = None
        self.user = None
        self.password = None
        self.temperature_topic = None
        self.humidity_topic = None
        self.display_topic = None
        self.light_topic = None
        self.brightness_topic = None


class LEDStripConfig:

    def __init__(self):
        self.length = None
        self.light = None
        self.max_brightness = None
        self.brightness = None


class InputsConfig:

    def __init__(self):
        self.buttons_light = None
        self.buttons_display = None


class TemperatureConfig:

    def __init__(self):
        self.sensor_ranges = None
        self.sensor_colours = None
        self.sensor_type = "Adafruit_DHT.AM2302"
        self.pin = 22
        self.update_seconds = 60


class TimingConfig:

    def __init__(self):
        self.speed_in_seconds = None
        self.menu_button_pressed_time_in_seconds = None
        self.menu_display = None


class DisplayModeConfig:

    def __init__(self):
        self.name = None
        self.menu = None
        self.background = None
