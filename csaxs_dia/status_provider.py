from logging import getLogger

from detector_integration_api.utils import ClientDisableWrapper

from csaxs_dia.validation_eiger9m import IntegrationStatus

_audit_logger = getLogger("audit_trail")
_logger = getLogger(__name__)


class CachedStatusProvider(object):
    def __init__(self, backend_client, writer_client, detector_client):
        self.backend_client = backend_client
        self.writer_client = writer_client
        self.detector_client = detector_client

        self._last_backend_status = None

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

    def get_cached_status_details(self):
        _audit_logger.info("Getting cached status details.")

        if not self._last_backend_status or \
                self._last_backend_status != IntegrationStatus.COMPONENT_NOT_RESPONDING.value:

            _logger.info("Cached backend status invalid %s. Trying to get real status." % self._last_backend_status)

            result = self.get_status_details()
            self._last_backend_status = result["backend"]

            return result

        _audit_logger.info("writer_client.get_status()")
        try:
            writer_status = self.writer_client.get_status() \
                if self.writer_client.is_client_enabled() else ClientDisableWrapper.STATUS_DISABLED
        except:
            writer_status = IntegrationStatus.COMPONENT_NOT_RESPONDING.value

        try:
            detector_status = self.detector_client.get_status() \
                if self.detector_client.is_client_enabled() else ClientDisableWrapper.STATUS_DISABLED
        except:
            detector_status = IntegrationStatus.COMPONENT_NOT_RESPONDING.value

        _logger.debug("Detailed cached status requested:\nWriter: %s\nBackend: %s\nDetector: %s",
                      writer_status, self._last_backend_status, detector_status)

        return {"writer": writer_status,
                "backend": self._last_backend_status,
                "detector": detector_status}



