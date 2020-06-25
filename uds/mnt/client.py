"""
VERSION: 1.0.1
Standard module to use the paho library for setting up a mqtt-client and connect to a given broker
for paho-mqtt docu, see https://pypi.org/project/paho-mqtt/
"""

import sys
import time
import logging
import requests
from threading import Thread
import json
import paho.mqtt.client as mqtt
import re


HOSTNAME = "3pi4"
MQTT_IP = "1.0.0.34"
MQTT_PORT = "1883"
logger = logging.getLogger(__name__)


class Client:
    """
    Setting up a client to publish and subscribe on given topics at a given borker address
    """

    def __init__(self, id=None, broker_adress=MQTT_IP, broker_port=MQTT_PORT):
        """ initialize client """
        logger.info('Initializing MQTT Client')
        self.broker_adress = broker_adress
        self.broker_port = broker_port
        self.client = mqtt.Client(HOSTNAME + "/" + id, clean_session=True, userdata=None, protocol=mqtt.MQTTv311, transport="tcp")
        self.subscribed = {} # suscribed topics and their on_message callbacks
        self.publish_callback = None

    def on_connect(self, client, userdata, flags, res_code):
        """
        post a message when broker is found and connected to,
        also do some more action, e. g. ... (?)
        """
        logger.info("MQTT Client connected with result code {}".format(res_code))
        # self.client.subscribe("3pi2/test")
        for topic in self.subscribed:
            logger.info("Subscribing to topic \"{}\"".format(topic))
            self.client.subscribe(topic)

    def on_disconnect(self, client, userdata, res_code):
        """ called on disconnect (client from broker) """
        logger.info("MQTT Client disconnected with result code {}".format(res_code))

    def on_subscribe(self, client, userdata, mid, granted_qos):
        logger.info("Successfully subscribed with userdata {}, message id {} and qos {}".format(userdata, mid, granted_qos))

    def on_unsubscribe(self, client, userdata, mid):
        """ called when the broker responds to an unsubscribe request """
        logger.debug("Successfully unsubscribed with userdata {}, message id {}".format(userdata, mid))

    def on_message(self, client, userdata, msg):
        logger.debug("Got a message on topic \"{}\", message {}".format(msg.topic, msg.payload))

        # if self.subscribed[msg.topic]:
        for key in self.subscribed:
            pattern = key.replace("#", ".*")
            pattern = pattern.replace("/", "\/")
            # logger.debug("pattern, topic: {}, {}".format(pattern, msg.topic))
            if re.match(pattern, msg.topic):
                # logger.debug("topic matches pattern")
                # use a thread to call the callback, to not block new publishes (etc.) in callback
                # see: https://github.com/eclipse/paho.mqtt.python/issues/234
                thread = Thread(target=self.subscribed[key], args=(self, msg))
                thread.start()
            # timestamp = int(time.time()*10**9)
        # payload = str(msg.topic) + ' value="' + str(msg.payload) + '" ' + str(timestamp)
        # response = requests.post('http://192.168.137.32:8086/write?db=mqttdb', data=payload)
        # logger.debug("Write message to influxdb, status: {}".format(response.text))

    def on_publish(self, client, userdata, mid):
        """
        triggered after complete transmission to the broker
        Info: usefull to use as a wait function e. g. before shutting down the client
        """
        # logger.debug("Successfully published with userdata {} and message id {} ".format(userdata, mid))
        if self.publish_callback:
            self.publish_callback(self)

    # def on_log(self, client, userdata, level, buf):
    #     """ gets called when the paho mqtt client has some log information """
    #     logger.debug("Got a level {} logging message: {}".format(level, buf))


    def run(self):
        """ bind paho methods and start client """
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.client.on_publish = self.on_publish
        # self.client.on_log = self.on_log
        # self.client.enable_logger(logger)
        self.client.reconnect_delay_set(min_delay=0.3, max_delay=120)
        try:
            self.client.connect(self.broker_adress, int(self.broker_port), 60)
        except:
            txt = 'Broker with ip-adress {} on port {} not found'.format(self.broker_adress, self.broker_port)
            logger.error(txt)
            raise Exception(txt)
            # sys.exit()
        # self.client.loop_forever()
        self.client.loop_start()
    
    def stop(self):
        """
        stops the infinite loop to keep the client alive,
        disconnects the client
        """
        self.client.disconnect()
        self.client.loop_stop()

    def subscribe(self, topic, func=None, qos=1):
        """ subscribe to a topic """
        topic = HOSTNAME + "/" + topic
        logger.debug("Subscribing to topic \"{}\"".format(topic))
        # self.client.subscribe(topic)
        self.subscribed[topic] = func
        self.client.subscribe(topic, qos)

    def unsubscribe(self, topic):
        """ unsubscribe from a topic """
        logger.info("Unsubscribing from topic \"{}\"".format(topic))
        self.client.unsubscribe(topic)
        del self.subscribed[topic]

    def publish(self, topic, message, qos=1, retain=False, func=None):
        """ publish a message on a topic """
        logger.debug("Publish message \"{}\" on topic \"{}\"".format(message, topic))
        if func:
            self.publish_callback = func
        self.client.publish(topic, message, qos, retain)

    def publishService(self, service, qos=1, retain=True):
        """ special publish function for Service Discovery services """
        topic = "services/" + HOSTNAME + "/" + service["request"]
        service["request"] = HOSTNAME + "/" + service["request"]
        logger.debug("Publish SD message \"{}\" on topic \"{}\"".format(service, topic))
        json_message = json.dumps(service)
        self.client.publish(topic, json_message, qos, retain)
