import signal
import unittest

from multiprocessing import Process
from time import sleep

import os
from detector_integration_api.tests.utils import start_test_integration_server

from csaxs_dia import manager


class TestReadme(unittest.TestCase):
    def setUp(self):
        self.host = "0.0.0.0"
        self.port = 10000

        self.dia_process = Process(target=start_test_integration_server, args=(self.host, self.port, manager))
        self.dia_process.start()

        # Give it some time to start.
        sleep(1)

    def tearDown(self):
        self.dia_process.terminate()
        sleep(0.5)

        os.kill(self.dia_process.pid, signal.SIGINT)

        # Wait for the server to die.
        sleep(1)

    def test_example(self):
        # Just some mock value for the file format.
        DEBUG_FORMAT_PARAMETERS = {}

        # Import the client.
        from detector_integration_api import DetectorIntegrationClient

        # Connect to the Eiger 9M DIA.
        client = DetectorIntegrationClient()

        # Make sure the status of the DIA is initialized.
        client.reset()

        # Write 1000 frames, as user id 11057 (gac-x12saop), to file "/sls/X12SA/Data10/gac-x12saop/tmp/dia_test.h5".
        writer_config = {"n_frames": 1000, "user_id": 11057,
                         "output_file": "/tmp/dia_test.h5"}

        # Expect 1000, 16 bit frames.
        backend_config = {"bit_depth": 16, "n_frames": 1000}

        # Acquire 1000, 16 bit images with a period of 0.02.
        detector_config = {"dr": 16, "frames": 1000, "period": 0.02, "exptime": 0.0001}

        # Add format parameters to writer. In this case, we use the debugging one.
        writer_config.update(DEBUG_FORMAT_PARAMETERS)

        configuration = {"writer": writer_config,
                         "backend": backend_config,
                         "detector": detector_config}

        # Set the configs.
        client.set_config(configuration)

        # Start the acquisition.
        client.start()

        # Get the current acquisition status (it should be "IntegrationStatus.RUNNING")
        client.get_status()

        # NOTE: It will never finish, because there is no stream.

        # Block until the acquisition has finished (this is optional).
        # client.wait_for_status("IntegrationStatus.FINISHED")
