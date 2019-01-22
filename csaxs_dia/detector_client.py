from sls_detector import Eiger


class EigerClientWrapper(object):
    def __init__(self):
        self.detector = Eiger()

    def start(self):
        self.detector.start_detector()

    def stop(self):
        self.detector.stop_detector()

    def set_config(self, configuration):
        for key, value in configuration.items():
            setattr(self.detector, key, value)

    def get_status(self):
        return self.detector.status

