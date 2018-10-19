# Import the client.
from detector_integration_api import DetectorIntegrationClient

# Connect to the Eiger 9M DIA.
client = DetectorIntegrationClient("http://xbl-daq-29:10000")

# Make sure the status of the DIA is initialized.
client.reset()

# Write 1000 frames, as user id 11057 (gac-x12saop), to file "/sls/X12SA/Data10/gac-x12saop/tmp/dia_test.h5".
writer_config = {"n_frames": 1000, "user_id": 11057, "output_file": "/sls/X12SA/Data10/gac-x12saop/tmp/dia_test.h5"}

# Expect 1000, 16 bit frames.
backend_config = {"bit_depth": 16, "n_frames": 1000}

# Acquire 1000, 16 bit images with a period of 0.02.
detector_config = {"dr": 16, "frames": 1000, "period": 0.02, "exptime": 0.0001}

configuration = {"writer": writer_config,
                 "backend": backend_config,
                 "detector": detector_config}

# Set the configs.
client.set_config(configuration)

# Start the acquisition.
client.start()

# Get the current acquisition status (it should be "IntegrationStatus.RUNNING")
client.get_status()

# Block until the acquisition has finished (this is optional).
client.wait_for_status("IntegrationStatus.FINISHED")