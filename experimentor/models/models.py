"""
MODELS
======
Models are a buffer between user interactions and real devices. Models should define at least some basic common properties,
for example how to read a value from a sensor and how to apply a value to an actuator.
Models can also take care of manipulating data, for example calculating an FFT and returning it to the user.

"""
from copy import deepcopy

from experimentor.core.model_properties import ModelProp


class Model:
    """
    Base class that is inherited by the rest of the models.
    """
    __driver__ = None
    _name = None
    _properties = []

    def __init__(self):
        if self.__driver__ is None:
            raise Exception('You should specify a driver by overwritting __driver__')

    @property
    def driver(self):
        return self.__driver__

    def apply_value(self, actuator, value):
        """ Method for applying a value to a given actuator.
        :param actuator: Instance of an Actuator
        :param value: Value to be passed to the driver. Ideally a Quantity."""
        pass

    def read_value(self, sensor):
        """ Method for reading a value from a given sensor.
        :param sensor: Instance of a Sensor.
        :type sensor: experimentor.Sensor
        :return: If possible a Quantity, if not whatever data type associated with the sensor.
        """
        return True

    def make_ramp(self, start, stop, step):
        """
        Method for making a ramp on an Actuator. It should be an actuator that allows making a ramp.
        :param start: Start value of the ramp
        :param stop: Stop value of the ramp
        :param step: Step of the ramp
        """
        pass

    def _collect_properties(self):
        for item in dir(self):
            if isinstance(item, ModelProp):
                prop = getattr(self, item)
                self._properties[item] = deepcopy(prop)

    def __str__(self):
        return "<Model {}>".format(self._name)