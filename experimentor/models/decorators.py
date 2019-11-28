from functools import wraps
from threading import Thread

from experimentor.lib.log import get_logger


def not_implemented(func):
    @wraps(func)
    def func_wrapper(cls, *args, **kwargs):
        logger = get_logger(__name__)
        logger.warning(f'{cls}.{func.__name__} Not Implemented')
        return func(cls, *args, **kwargs)
    return func_wrapper


def make_async_thread(func):
    """ Simple decorator to make a method run on a separated thread. This decorator will not work on simple
    functions, since it requires the first argument to be an instantiated class (self).
    It will store the method in an attribute of the class, called `_threads``, or it will create it if it does not
    exist yet.

    TODO: Check what happens with the _thread list and inherited classes. Is there a risk that the list will be
        shared? If the list is defined as a class attribute instead of an object attribute, most likely it will. If
        it is defined outside of the scope and then linked to the class, also.

    .. warning:: In complex scenarios, this simple decorator can give raise to mistakes, i.e. objects having access
        to other objects threads.

    .. TODO: May be wise to use this decorator only with certain models, and define a method directly in them to
        manipulate the threads, avoiding the inherent problems of mutable types.

    """
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        logger = get_logger(name=__name__)
        logger.info('Starting new thread for {}'.format(func.__name__))
        if not hasattr(args[0], '_threads'):
            args[0]._threads = []

        elif not isinstance(args[0]._threads, list):
            raise ValueError('The variable _threads must be a list in order to store a new Thread in it')

        args[0]._threads.append([func.__name__, Thread(target=func, args=args, kwargs=kwargs)])
        args[0]._threads[-1][1].start()
        logger.info('In total there are {} threads'.format(len(args[0]._threads)))

    return func_wrapper


