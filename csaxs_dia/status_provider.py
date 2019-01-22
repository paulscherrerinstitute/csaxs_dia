from logging import getLogger

from detector_integration_api.utils import ClientDisableWrapper
from time import time
from csaxs_dia.validation_eiger9m import IntegrationStatus
from csaxs_dia.detector_client import EigerClientWrapper

_audit_logger = getLogger("audit_trail")
_logger = getLogger(__name__)


class CachedStatusProvider(object):
    def __init__(self, backend_client, writer_client, detector_client):
        self.backend_client = backend_client
        self.writer_client = writer_client
        self.detector_client = detector_client

        self.eiger = EigerClientWrapper()

        self._last_backend_status = None
        self._last_writer_status = None
        self._last_detector_status = None

    def get_status_details(self):

        _audit_logger.info("Getting status details.")

        _audit_logger.info("writer_client.get_status()")
        try:
            writer_status = self.writer_client.get_status() \
                if self.writer_client.is_client_enabled() else ClientDisableWrapper.STATUS_DISABLED
        except:
            writer_status = IntegrationStatus.COMPONENT_NOT_RESPONDING.value
        self._last_writer_status = writer_status

        # TODO: Remove this once we are sure this statuses are not needed to operate the detector.
        backend_status = None
        detector_status = None

        _logger.debug("Detailed status requested:\nWriter: %s\nBackend: %s\nDetector: %s",
                      writer_status, backend_status, detector_status)

        return {"writer": writer_status,
                "backend": backend_status,
                "detector": detector_status}

