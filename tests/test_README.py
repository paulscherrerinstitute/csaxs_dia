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
        DEBUG_FORMAT_PARAMETERS = {
            "sl2wv": 1.0, "sl0ch": 1.0, "sl2wh": 1.0, "temp_mono_cryst_1": 1.0, "harmonic": 1,
            "mokev": 1.0, "sl2cv": 1.0, "bpm4_gain_setting": 1.0, "mirror_coating": "placeholder text",
            "samx": 1.0, "sample_name": "placeholder text", "bpm5y": 1.0, "sl2ch": 1.0, "curr": 1.0,
            "bs2_status": "placeholder text", "bs2y": 1.0, "diode": 1.0, "samy": 1.0, "sl4ch": 1.0,
            "sl4wh": 1.0, "temp_mono_cryst_2": 1.0, "sl3wh": 1.0, "mith": 1.0, "bs1_status": "placeholder text",
            "bpm4s": 1.0, "sl0wh": 1.0, "bpm6z": 1.0, "bs1y": 1.0, "scan": "placeholder text", "bpm5_gain_setting": 1.0,
            "bpm4z": 1.0, "bpm4x": 1.0, "date": "placeholder text", "mibd": 1.0, "temp": 1.0,
            "idgap": 1.0, "sl4cv": 1.0, "sl1wv": 1.0, "sl3wv": 1.0, "sl1ch": 1.0, "bs2x": 1.0, "bpm6_gain_setting": 1.0,
            "bpm4y": 1.0, "bpm6s": 1.0, "sample_description": "placeholder text", "bpm5z": 1.0, "moth1": 1.0,
            "sec": 1.0, "sl3cv": 1.0, "bs1x": 1.0, "bpm6_saturation_value": 1.0, "bpm5s": 1.0, "mobd": 1.0,
            "sl1wh": 1.0, "sl4wv": 1.0, "bs2_det_dist": 1.0, "bpm5_saturation_value": 1.0,
            "fil_comb_description": "placeholder text", "bpm5x": 1.0, "bpm4_saturation_value": 1.0, "bs1_det_dist": 1.0,
            "sl3ch": 1.0, "bpm6y": 1.0, "sl1cv": 1.0, "bpm6x": 1.0, "ftrans": 1.0, "samz": 1.0
        }

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
