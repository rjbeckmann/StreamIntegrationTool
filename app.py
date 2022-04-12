import configparser
import logging
import traceback
from datetime import datetime


class Configy:
    pass


class App():
    _configuration = None

    @staticmethod
    def config():
        if App._configuration is None:
            conf = configparser.ConfigParser()
            conf.read('config.txt')
            App._configuration = Configy()
            for key in conf.keys():
                print(key)
                setattr(App._configuration, key, Configy())
                for k,v in conf[key].items():
                    current = getattr(App._configuration, key)
                    setattr(current, k, v)

        return App._configuration


class Logger:

    def __init__(self, name):
        level = getattr(logging, App.config().main.log_level.upper())
        logging.basicConfig(
            filename=App.config().main.log_file,
            encoding='utf-8',
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(name)

    def error(self, message):
        self.logger.error(message)
        self.logger.error(traceback.format_exc())

    def info(self, message):
        self.logger.info(message)