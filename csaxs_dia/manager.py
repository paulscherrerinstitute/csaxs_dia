from copy import copy
from logging import getLogger

from detector_integration_api.utils import check_for_target_status
from csaxs_dia import validation_eiger9m
from csaxs_dia.validation_eiger9m import IntegrationStatus

_logger = getLogger(__name__)
_audit_logger = getLogger("audit_trail")


def try_catch(func, error_message_prefix):
    def wrapped(*args, **kwargs):

        try:
            return func(*args, **kwargs)
        except Exception as e:
            _audit_logger.error(error_message_prefix, e)

    return wrapped


class IntegrationManager(object):
    def __init__(self, backend_client, writer_client, detector_client, status_provider):
        self.backend_client = backend_client
        self.writer_client = writer_client
        self.detector_client = detector_client
        self.status_provider = status_provider

        self._last_set_backend_config = {}
        self._last_set_writer_config = {}
        self._last_set_detector_config = {}

        self.last_config_successful = False

    def start_acquisition(self, parameters):

        _audit_logger.info("Starting acquisition.")

        status = self.get_acquisition_status()
 
        if status != IntegrationStatus.READY:
            raise ValueError("Cannot start acquisition in %s state." % status)

        _audit_logger.info("self.set_acquisition_config()")
        self._set_acquisition_config(parameters)

        _audit_logger.info("writer_client.start()")
        self.writer_client.start()

        _audit_logger.info("detector_client.start()")
        self.detector_client.start()

        _audit_logger.info("Acquisition started.")

        # We need the status READY for very short acquisitions.
        return check_for_target_status(self.get_acquisition_status,
                                       (IntegrationStatus.RUNNING, IntegrationStatus.READY))

    def stop_acquisition(self):
        _audit_logger.info("Stopping acquisition.")

        status = self.get_acquisition_status()

        if status == IntegrationStatus.RUNNING:

            _audit_logger.info("detector_client.stop()")
            try_catch(self.detector_client.stop, "Error while trying to stop the detector.")()

            _audit_logger.info("writer_client.stop()")
            try_catch(self.writer_client.stop, "Error while trying to stop the writer.")()

        return check_for_target_status(self.get_acquisition_status, IntegrationStatus.READY)

    def get_acquisition_status(self):
        status = validation_eiger9m.interpret_status(self.status_provider.get_quick_status_details())
        return status

    def get_status_details(self):
        return self.status_provider.get_complete_status_details()

    def get_acquisition_status_string(self):
        return str(self.get_acquisition_status())

    def get_acquisition_config(self):
        # Always return a copy - we do not want this to be updated.
        return {"writer": copy(self._last_set_writer_config),
                "backend": copy(self._last_set_backend_config),
                "detector": copy(self._last_set_detector_config)}

    def set_acquisition_config(self, new_config):
        status = self.get_acquisition_status()

        if status != IntegrationStatus.READY:
            raise ValueError("Cannot set config in status %s. Please reset() first." % status)

        self._set_acquisition_config(new_config)

        return check_for_target_status(self.get_acquisition_status, IntegrationStatus.READY)      

    def _set_acquisition_config(self, new_config):

        writer_config = new_config.get("writer", {})
        backend_config = new_config.get("backend", {})
        detector_config = new_config.get("detector", {})

        last_config_successful = self.last_config_successful
        self.last_config_successful = False

        _audit_logger.info("Set acquisition configuration:\n"
                           "Writer config: %s\n"
                           "Backend config: %s\n"
                           "Detector config: %s\n",
                           writer_config, backend_config, detector_config)

        # Before setting the new config, validate the provided values. All must be valid.
        if self.writer_client.client_enabled:
            validation_eiger9m.validate_writer_config(writer_config)

        if self.backend_client.client_enabled:
            validation_eiger9m.validate_backend_config(backend_config)

        if self.detector_client.client_enabled:
            validation_eiger9m.validate_detector_config(detector_config)

        validation_eiger9m.validate_configs_dependencies(writer_config, backend_config, detector_config)

        if not last_config_successful or \
                (last_config_successful and self._last_set_backend_config != backend_config):

            _logger.info("Backend configuration changed. Restarting and applying config %s.", backend_config)

            _audit_logger.info("backend_client.close()")
            self.backend_client.reset()

            _audit_logger.info("backend_client.set_config(backend_config)")
            self.backend_client.set_config(backend_config)

            _audit_logger.info("backend_client.open()")
            self.backend_client.open()

            self._last_set_backend_config = backend_config
        else:
            _logger.info("Backend config did not change. Skipping.")

        _audit_logger.info("writer_client.set_parameters(writer_config)")
        self.writer_client.set_parameters(writer_config)
        self._last_set_writer_config = writer_config

        if not last_config_successful or \
                (last_config_successful and self._last_set_detector_config != detector_config):

            _logger.info("Detector configuration changed. Applying config %s.", detector_config)

            _audit_logger.info("detector_client.set_config(detector_config)")
            self.detector_client.set_config(detector_config)

            self._last_set_detector_config = detector_config
        else:
            _logger.info("Detector config did not change. Skipping.")

        self.last_config_successful = True

    def update_acquisition_config(self, config_updates):
        current_config = self.get_acquisition_config()

        _logger.debug("Updating acquisition config: %s", current_config)

        def update_config_section(section_name):
            if section_name in config_updates and config_updates.get(section_name):
                current_config[section_name].update(config_updates[section_name])

        update_config_section("writer")
        update_config_section("backend")
        update_config_section("detector")

        return self.set_acquisition_config(current_config)

    def set_clients_enabled(self, client_status):

        if "backend" in client_status:
            self.backend_client.set_client_enabled(client_status["backend"])
            _logger.info("Backend client enable=%s.", self.backend_client.is_client_enabled())

        if "writer" in client_status:
            self.writer_client.set_client_enabled(client_status["writer"])
            _logger.info("Writer client enable=%s.", self.writer_client.is_client_enabled())

        if "detector" in client_status:
            self.detector_client.set_client_enabled(client_status["detector"])
            _logger.info("Detector client enable=%s.", self.detector_client.is_client_enabled())

    def get_clients_enabled(self):
        return {"backend": self.backend_client.is_client_enabled(),
                "writer": self.writer_client.is_client_enabled(),
                "detector": self.detector_client.is_client_enabled()}

    def reset(self):
        _audit_logger.info("Resetting integration api.")

        self.last_config_successful = False
        self._last_set_backend_config = {}
        self._last_set_writer_config = {}
        self._last_set_detector_config = {}

        _audit_logger.info("detector_client.stop()")
        try_catch(self.detector_client.stop, "Error while trying to reset the detector.")()

        _audit_logger.info("backend_client.reset()")
        try_catch(self.backend_client.reset, "Error while trying to reset the backend.")()

        _audit_logger.info("writer_client.reset()")
        try_catch(self.writer_client.reset, "Error while trying to reset the writer.")()

        return check_for_target_status(self.get_acquisition_status, IntegrationStatus.READY)

    def kill(self):
        _audit_logger.info("Killing acquisition.")

        _audit_logger.info("detector_client.stop()")
        try_catch(self.detector_client.stop, "Error while trying to kill the detector.")()

        _audit_logger.info("backend_client.reset()")
        try_catch(self.backend_client.reset, "Error while trying to kill the backend.")()

        _audit_logger.info("writer_client.kill()")
        try_catch(self.writer_client.kill, "Error while trying to kill the writer.")()

        return self.reset()

    def get_server_info(self):
        return {
            "clients": {
                "backend_url": self.backend_client.backend_url,
                "writer_url": self.writer_client.url},
            "clients_enabled": self.get_clients_enabled(),
            "validator": "NOT IMPLEMENTED",
            "last_config_successful": self.last_config_successful
        }

    def get_metrics(self):
        # Always return a copy - we do not want this to be updated.
        return {"writer": self.writer_client.get_statistics(),
                "backend": self.backend_client.get_metrics(),
                "detector": {}}

    def test_daq(self, test_configuration):
        return "No daq test implemented yet."
