# -*- coding: utf-8; -*-
"""Unit tests for nightlightpi.config

There are no integration tests here. Just basic unit tests to verify
the behavior of load_config. Note that load_yaml is exported from
config.py in order to facilitate unit testing. It could be used by
external callers, but it probably shouldn't be.

"""

from unittest import TestCase
from unittest.mock import patch

from nightlightpi import errorstrings
from nightlightpi.config import load_config
from nightlightpi.config import ENVCONFIGPATH
from nightlightpi.config import ETCPATH


class LoadConfigTestCase(TestCase):

    @patch("nightlightpi.config.load_valid_yaml")
    def test_loads_from_env_var_if_set(self, mock_load_yaml):
        mock_load_yaml.return_value = self.test_config
        with patch.dict("os.environ", {ENVCONFIGPATH: "some.yaml"}):
            conf = load_config()
        mock_load_yaml.assert_called_once_with("some.yaml")

    @patch("nightlightpi.config.load_valid_yaml")
    def test_falls_back_to_ETCPATH_when_env_var_not_set(self, mock_load_yaml):
        mock_load_yaml.return_value = self.test_config
        with patch.dict("os.environ", {}):
            conf = load_config()
        mock_load_yaml.assert_called_once_with(ETCPATH)

    def setUp(self):
        self.test_config = {'display_modes': [{'background': None,
                                               'menu': 'images/menu_off.ppm',
                                               'name': 'Off'},
                                              {'background': 'images/temperature.ppm',
                                               'menu': 'images/menu_temperature.ppm',
                                               'name': 'Temperature'},
                                              {'background': None,
                                               'menu': 'images/menu_rainbow.ppm',
                                               'name': 'Rainbow'}],
                            'inputs': {'buttons_display': 24, 'buttons_light': 23},
                            'led_strip': {'brightness': 6,
                                          'length': 10,
                                          'light': 10,
                                          'max_brightness': 30},
                            'mqtt': {'brightness_topic': 'nightlight/brightness',
                                     'display_topic': 'nightlight/display',
                                     'enable': True,
                                     'humidity_topic': 'nightlight/humidity',
                                     'light_topic': 'nightlight/light',
                                     'password': 'PASSWORD',
                                     'port': 8883,
                                     'server': 'SERVER',
                                     'temperature_topic': 'nightlight/temperature',
                                     'user': 'USERNAME'},
                            'temperature': {'sensor_colours': [{'b': 255, 'g': 0, 'r': 20},
                                                              {'b': 10, 'g': 200, 'r': 255},
                                                              {'b': 0, 'g': 128, 'r': 255},
                                                              {'b': 0, 'g': 0, 'r': 255}],
                                            'sensor_ranges': [16, 20, 23.9]},
                            'timing': {'menu_button_pressed_time_in_seconds': 0,
                                       'menu_display': 0,
                                       'speed_in_seconds': 1}}
