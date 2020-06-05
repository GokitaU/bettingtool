import pika
from extractor.sample.workers.worker import Worker
from extractor.sample.messaging.messaging_config_keys import MessagingConfigKeys
from multiprocessing import get_logger

class Consumer(Worker):
    def __init__(self, name, config):
        """
        Initialize consumer with given config and name and calls connect_to_broker
        to establish the connection with the message broker.
        """
        self.logger = get_logger()
        self.load_consumer_config(config)
        super().__init__(name, self.wait_time)
        self.connect_to_broker()
    
    def load_consumer_config(self, config):
        self.logger.info(f"initializing consumer with {config}")
        self.host_name = config[MessagingConfigKeys.host_name()]
        self.durable = config[MessagingConfigKeys.durable()]
        self.queue_name = config[MessagingConfigKeys.queue_name()]
        self.prefetch_count = config[MessagingConfigKeys.prefetch_count()]
        self.wait_time = config[MessagingConfigKeys.wait_time()]

    def connect_to_broker(self):
        """
        Establishes the connection with the message broker
        using the consumer configuration.
        """
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host_name))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name, durable=self.durable)
        self.channel.basic_qos(prefetch_count=self.prefetch_count)
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.receive)

    def run(self, shutdown_event):
        """
        Main method which starts the message consuming process.
        """
        try:
            self.logger.info("starting consuming")
            self.channel.start_consuming()
        except KeyboardInterrupt as error:
            self.channel.close()

    def receive(self, ch, method, properties, body):
        """
        Abstract method to be implemented by each specific consumer.
        This is the signature for the pika client's on_message_callback method.
        """
        pass