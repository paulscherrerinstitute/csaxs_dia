from copy import copy
from logging import getLogger

from detector_integration_api.utils import ClientDisableWrapper, check_for_target_status

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
    def __init__(self, backend_client, writer_client, detector_client):
        self.backend_client = ClientDisableWrapper(backend_client)
        self.writer_client = ClientDisableWrapper(writer_client)
        self.detector_client = ClientDisableWrapper(detector_client)

        self._last_set_backend_config = {}
        self._last_set_writer_config = {}
        self._last_set_detector_config = {}

        self.last_config_successful = False

    def start_acquisition(self, *args, **kwargs):
        _audit_logger.info("Starting acquisition.")

        status = self.get_acquisition_status()
        if status != IntegrationStatus.READY:
            raise ValueError("Cannot start acquisition in %s state." % status)

        _audit_logger.info("writer_client.start()")
        self.writer_client.start()

        _audit_logger.info("detector_client.start()")
        self.detector_client.start()

        # We need the status FINISHED for very short acquisitions.
        return check_for_target_status(self.get_acquisition_status,
                                       (IntegrationStatus.RUNNING,
                                        IntegrationStatus.DETECTOR_STOPPED,
                                        IntegrationStatus.FINISHED))

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
        status = validation_eiger9m.interpret_status(self.get_status_details(), self.last_config_successful)

        # There is no way of knowing if the detector is configured as the user desired.
        # We have a flag to check if the user config was passed on to the detector.
        if status == IntegrationStatus.READY and self.last_config_successful is False:
            return IntegrationStatus.ERROR

        return status

    def get_acquisition_status_string(self):
        return str(self.get_acquisition_status())

    def get_status_details(self):
        _audit_logger.info("Getting status details.")

        _audit_logger.info("writer_client.get_status()")
        try:
            writer_status = self.writer_client.get_status() \
                if self.writer_client.is_client_enabled() else ClientDisableWrapper.STATUS_DISABLED
        except:
            writer_status = IntegrationStatus.COMPONENT_NOT_RESPONDING.value

        _audit_logger.info("backend_client.get_status()")
        try:
            backend_status = self.backend_client.get_status() \
                if self.backend_client.is_client_enabled() else ClientDisableWrapper.STATUS_DISABLED
        except:
            backend_status = IntegrationStatus.COMPONENT_NOT_RESPONDING.value

        _audit_logger.info("detector_client.get_status()")
        try:
            detector_status = self.detector_client.get_status() \
                if self.detector_client.is_client_enabled() else ClientDisableWrapper.STATUS_DISABLED
        except:
            detector_status = IntegrationStatus.COMPONENT_NOT_RESPONDING.value

        _logger.debug("Detailed status requested:\nWriter: %s\nBackend: %s\nDetector: %s",
                      writer_status, backend_status, detector_status)

        return {"writer": writer_status,
                "backend": backend_status,
                "detector": detector_status}

    def get_acquisition_config(self):
        # Always return a copy - we do not want this to be updated.
        return {"writer": copy(self._last_set_writer_config),
                "backend": copy(self._last_set_backend_config),
                "detector": copy(self._last_set_detector_config)}

    def set_acquisition_config(self, new_config):

        writer_config = new_config.get("writer", {})
        backend_config = new_config.get("backend", {})
        detector_config = new_config.get("detector", {})

        status = self.get_acquisition_status()

        last_config_successful = self.last_config_successful
        self.last_config_successful = False

        if status not in (IntegrationStatus.INITIALIZED, IntegrationStatus.READY):
            raise ValueError("Cannot set config in %s state. Please stop or reset first." % status)

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

        if last_config_successful and self._last_set_backend_config != backend_config:

            _logger.info("Backend configuration changed. Restarting and applying config %s.", backend_config)

            _audit_logger.info("backend_client.close()")
            self.backend_client.close()

            _audit_logger.info("backend_client.set_config(backend_config)")
            self.backend_client.set_config(backend_config)

            _audit_logger.info("backend_client.open()")
            self.backend_client.open()

            self._last_set_backend_config = backend_config

        _audit_logger.info("writer_client.set_parameters(writer_config)")
        self.writer_client.set_parameters(writer_config)
        self._last_set_writer_config = writer_config

        if last_config_successful and self._last_set_detector_config != detector_config:

            _logger.info("Detector configuration changed. Applying config %s.", detector_config)

            _audit_logger.info("detector_client.set_config(detector_config)")
            self.detector_client.set_config(detector_config)

            self._last_set_detector_config = detector_config

        self.last_config_successful = True

        return check_for_target_status(self.get_acquisition_status, IntegrationStatus.READY)

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

        return check_for_target_status(self.get_acquisition_status, IntegrationStatus.INITIALIZED)

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
