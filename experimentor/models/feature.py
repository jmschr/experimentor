"""
    Features
    ========
    Features in a model are those parameters that can be read, set, or both. They were modeled after Lantz Feat objects,
    and the idea is that they can encapsulate common patterns in device control. They are similar to :mod:`~Settings` in
    behavior, except for the absence of a cache. Features do communicate with the device when reading a value.

    For example, a feature could be the value of an analog input on a DAQ, or the temperature of a camera. They are
    meant to be part of a measurement, for example their values can change in loops in order to make a scan. Features can
    be used as decorators in pretty much the same way @propery can be used. The only difference is that they register in
    the models properties object, so it is possible to update values either by submitting a value directly to the Feature
    or by sending a dictionary to the properties and updating all at once.

    It is possible to mark a feature as a setting. In this case, the value will not be read from the device, but it will
    be cached. In case it is needed to refresh a value from the device, it is possible to use a specific argument, such
    as ``None``. For example::

        @Feature(setting=True, force_update_arg=0)
        def exposure(self):
            self.driver.get_exposure()

        @exposure.setter
        def exposure(self, exposure_time):
            self.driver.set_exposure(exposure_time)

    .. TODO:: It is possible to define complex behavior such as unit conversion, limit checking, etc. We should narrow
        down what is appropriate for a model and what should go into the Controller.

    .. TODO:: A useful pattern is to catch the exception raised by the controllers if a value is out of range, or with
        the wrong units.
"""


class Feature:
    """Properties that belong to models. It makes easier the setting and getting of attributes, while at the same
    time it keeps track of the properties of each model.
    """

    name = ''
    kwargs = None

    def __init__(self, fget=None, fset=None, fdel=None, doc=None, **kwargs):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        if doc is None and fget is not None:
            doc = fget.__doc__
        self.__doc__ = doc
        self.kwargs = kwargs
        self.owner = None

        self.is_setting = self.kwargs.get('setting', False)
        self.force_update = self.kwargs.get('force_update_arg', None)
        self.value = None

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if self.fget is None:
            raise AttributeError("unreadable attribute")

        if self.is_setting and self.value != self.force_update:
            return self.value

        val = self.fget(instance)
        instance.config.upgrade({self.name: val}, force=True)
        return val

    def __set__(self, instance, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        if self.is_setting and self.force_update == value:
            value = self.fget(instance)
        else:
            self.fset(instance, value)
        self.value = value
        instance.config.upgrade({self.name: value}, force=True)

    def __set_name__(self, owner, name):
        # The following code is to work around inheritance in only one direction. This means that only child classes
        # should inherit properties of their parents, but not the other way around.
        model_props = owner._model_props
        if getattr(model_props, 'model_name', None) != object.__qualname__:
            # If the name of the class is different from the name registered as a property, we must create a new
            # instance, using the information already available

            model_props = model_props.__class__(**model_props)
            setattr(model_props, 'model_name', object.__qualname__)
            owner._model_props = model_props

        owner._model_props[name] = self

    def __call__(self, func):
        if self.fget is None:
            return self.getter(func)
        return self.setter(func)

    def getter(self, fget):
        return type(self)(fget, self.fset, self.fdel, self.__doc__, **self.kwargs)

    def setter(self, fset):
        return type(self)(self.fget, fset, self.fdel, self.__doc__, **self.kwargs)

    def deleter(self, fdel):
        return type(self)(self.fget, self.fset, fdel, self.__doc__, **self.kwargs)

