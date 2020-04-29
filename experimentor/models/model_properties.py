"""
    In order to simplify the update of values in models, we can define ModelProps. They can be used as decorators in
    pretty much the same way @propery can be used. The only difference is that they register in the models properties
    object, so it is possible to update values either by submitting a value directly to the ModelProp or by sending
    a dictionary to the properties and updating all at once.
"""


class ModelProp:
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

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        self.instance = instance
        val = self.fget(instance)
        instance.config.upgrade({self.name: val}, force=True)
        return val

    def __set__(self, instance, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(instance, value)
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

