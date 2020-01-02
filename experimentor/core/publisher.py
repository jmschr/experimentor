# -*- coding: utf-8 -*-
"""
Publisher
=========

Publishers are responsible for broadcasting the message over the ZMQ PUB/SUB architecture. The publisher runs
continuously on a separated process and grabs elements from a queue, which in turn are sent through a socket to any
other processes listening.

.. TODO:: In the current implementation, data is serialized for being added to a Queue, then deserialized by the
    publisher and serialized again to be sent. These three steps could be simplify into one if, for example, one assumes
    that objects where pickled. There is also a possibility of assuming numpy arrays and using a zero-copy strategy.

:copyright:  Aquiles Carattino <aquiles@uetke.com>
:license: GPLv3, see LICENSE for more details
"""
from multiprocessing import Process
from time import sleep
import zmq

from experimentor.config import settings
from experimentor.lib.log import get_logger


class Publisher(Process):
    """ Publisher class in which the queue for publishing messages is defined and also a separated process is started.
    It is important to have a new process, since the serialization/deserialization of messages from the QUEUE may be
    a bottleneck for performance.
    """
    def __init__(self, event):
        super(Publisher, self).__init__()
        self.logger = get_logger(name=__name__)
        self._event = event   # This event is used to stop the process

    def run(self):
        """ Start a new process that will be responsible for broadcasting the messages.

            .. TODO:: Find a way to start the publisher on a different port if the one specified is in use.
        """
        self.logger.info('Publisher initializing')
        context = zmq.Context()
        publisher = context.socket(zmq.PUB)
        try:
            publisher.bind(f"tcp://*:{settings.PUBLISHER_PUBLISH_PORT}")
        except zmq.ZMQError:
            self.logger.error('Por already in use. Trying to close and reconnect')
            temp = context.socket(zmq.PUSH)
            temp.connect(f"tcp://127.0.0.1:{settings.PUBLISHER_PULL_PORT}")
            temp.send_string("", zmq.SNDMORE)
            temp.send_pyobj(settings.PUBLISHER_EXIT_KEYWORD)
            sleep(1)
            self.logger.info('Retrying to open the publisher')
            try:
                publisher.bind(f"tcp://*:{settings.PUBLISHER_PUBLISH_PORT}")
            except zmq.ZMQError:
                raise

        listener = context.socket(zmq.PULL)
        listener.bind(f"tcp://127.0.0.1:{settings.PUBLISHER_PULL_PORT}")

        sleep(2)  # To give time to binding to the given port
        i = 0
        self.logger.info('Publisher ready to handle events')
        while not self._event.is_set():
            topic = listener.recv_string()
            self.logger.debug(f"Got data on topic {topic}")
            data = listener.recv_pyobj()
            i += 1
            self.logger.debug(data)
            publisher.send_string(topic, zmq.SNDMORE)
            publisher.send_pyobj(data)

            if topic is "":
                self.logger.info('Got Broad Topic')
                if isinstance(data, str) and data == settings.PUBLISHER_EXIT_KEYWORD:
                    self.logger.info('Stopping the Publisiher')
                    self._event.set()

    def stop(self):
        with Listener() as listener:
            listener.publish(settings.PUBLISHER_EXIT_KEYWORD)
        self._event.set()


class Listener:
    def __init__(self):
        context = zmq.Context()
        self.listener = context.socket(zmq.PUSH)
        self.listener.connect(f"tcp://127.0.0.1:{settings.PUBLISHER_PULL_PORT}")
        sleep(1)
        self.logger = get_logger()
        self.i = 0

    def publish(self, data, topic=""):
        self.listener.send_string(topic, zmq.SNDMORE)
        self.listener.send_pyobj(data)
        self.i += 1

    def finish(self):
        self.logger.info('Finishing listener')
        self.listener.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()

    def __enter__(self):
        return self


"""
TODO: The definition of publisher and subscriber in here may be a very bad idea!
"""

publisher = Publisher(settings.GENERAL_STOP_EVENT)
listener = Listener()
