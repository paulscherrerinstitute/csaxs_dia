from sls_detector import Eiger


class DetectorClientWrapper(object):
    def __init__(self):
        self.detector = Eiger()

    def start(self):
        self.eiger.start_detector()

    def stop(self):
        self.eiger.stop_detector()

    def set_config(self, configuration):
        for key, value in configuration.items():
            setattr(self.eiger, key, value)

    def get_status(self):
        return self.eiger.status

