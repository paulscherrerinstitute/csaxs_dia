[![Build Status](https://travis-ci.org/paulscherrerinstitute/csaxs_dia.svg?branch=master)](https://travis-ci.org/paulscherrerinstitute/csaxs_dia)

# cSAXS Eiger 9M detector integration

The following README is useful for controlling the Eiger 9M deployment at cSAXS.

The detector integration is made up from the following components:

- Detector integration API (running on xbl-daq-29)
    - https://github.com/datastreaming/detector_integration_api
- Detector client (running on xbl-daq-29)
    - https://github.com/slsdetectorgroup/slsDetectorPackage
- Backend server (running on xbl-daq-28)
    - https://git.psi.ch/HPDI/dafl.psidet
- Writer process (running on xbl-daq-29)
    - https://github.com/paulscherrerinstitute/lib_cpp_h5_writer
    
# Table of content
1. [Quick introduction](#quick)
    1. [Python client](#quick_python)
    2. [Rest API](#quick_rest)
2. [State machine](#state_machine)
3. [DIA configuration parameters](#dia_configuration_parameters)
    1. [Detector configuration](#dia_configuration_parameters_detector)
    2. [Backend configuration](#dia_configuration_parameters_backend)
    3. [Writer configuration](#dia_configuration_parameters_writer)
4. [xbl-daq-28 (Backend server)](#deployment_info_28)
5. [xbl-daq-27 (DIA and writer server)](#deployment_info_27)

<a id="quick"></a>
## Quick introduction

**DIA Address:** http://xbl-daq-29:10000

To get a feeling on how to use the DIA, you can use the following example to start and write a test file.

You can control the DIA via the Python client or over the REST api directly.

**More documentation about the DIA can be found on its repository** (referenced above).

<a id="quick_python"></a>
### Python client

To use the Python client you need to source our central Python:
```bash
source /opt/gfa/python
```
or you can install it using conda:
```bash
conda install -c paulscherrerinstitute detector_integration_api
```

If you login as dia on xbl-daq-29 you will have the dia client available as well.

```python
# Import the client.
from detector_integration_api import DetectorIntegrationClient

# Connect to the Eiger 9M DIA.
client = DetectorIntegrationClient("http://xbl-daq-29:10000")

# Make sure the status of the DIA is initialized.
client.reset()

# Write 1000 frames, as user id 11057 (gac-x12saop), to file "/gpfs/perf/X12SA/Data10/gac-x12saop/tmp/dia_test.h5".
writer_config = {"n_frames": 1000, "user_id": 11057, "output_file": "/gpfs/perf/X12SA/Data10/gac-x12saop/tmp/dia_test.h5"}

# Expect 1000, 16 bit frames.
backend_config = {"bit_depth": 16, "n_frames": 1000, "preview_modulo": 10}

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

```

<a id="quick_rest"></a>
### Rest API

The direct calls to the REST Api will be shown with cURL. 

Responses from the server are always JSONs. The "state" attribute in the JSON response is:

- **"ok"**: The server processed your request successfully
    - Response example: {"state": "ok", "status": "IntegrationStatus.INITIALIZED"}
- **"error"**: An error happened on the server. The field **"status"** will tell you what is the problem.
    - Response example: {"state": "error", "status": "Specify config JSON with 3 root elements..."}

**Tip**: You can get a user id by running:
```bash
# Get the id for user gac-x12saop
id -u gac-x12saop
```

```bash
# Make sure the status of the DIA is initialized.
curl -X POST http://xbl-daq-29:10000/api/v1/reset

# Write 1000 frames, as user id 11057 (gac-x12saop), to file "/gpfs/perf/X12SA/Data10/gac-x12saop/tmp/dia_test.h5".
curl -X PUT http://xbl-daq-29:10000/api/v1/config -H "Content-Type: application/json" -d '
{"backend": {"bit_depth": 16, "n_frames": 10, "preview_modulo": 10},
 "detector": {"dr": 16, "exptime": 1, "frames": 10, "period": 0.1, "exptime": 0.001},
 "writer": {
  "n_frames": 10,
  "output_file": "/gpfs/perf/X12SA/Data10/gac-x12saop/tmp/dia_test.h5",
  "user_id": 11057
 }
}'

# Start the acquisition.
curl -X POST http://xbl-daq-29:10000/api/v1/start

# Get integration status.
curl -X GET http://xbl-daq-29:10000/api/v1/status

# Stop the acquisition. This should be called only in case of emergency:
#   by default it should stop then the selected number of images is collected.
curl -X POST http://xbl-daq-29:10000/api/v1/stop
```

<a id="state_machine"></a>
## State machine

The table below describes the possible states of the integration and the methods that cause a transition 
(this are also the methods that are allowed for a defined state).

Methods that do not modify the state machine are not described in this table, as they can be executed in every state.

| State | State description | Transition method | Next state |
|-------|-------------------|-------------------|------------|
| IntegrationStatus.INITIALIZED | Integration ready for configuration. |||
| | | set_config | IntegrationStatus.CONFIGURED |
| | | set_last_config | IntegrationStatus.CONFIGURED |
| | | update_config | IntegrationStatus.CONFIGURED |
| | | stop | IntegrationStatus.INITIALIZED |
| | | reset | IntegrationStatus.INITIALIZED |
| IntegrationStatus.CONFIGURED | Acquisition configured. |||
| | | start | IntegrationStatus.RUNNING |
| | | set_config | IntegrationStatus.CONFIGURED |
| | | set_last_config | IntegrationStatus.CONFIGURED |
| | | update_config | IntegrationStatus.CONFIGURED |
| | | stop | IntegrationStatus.INITIALIZED |
| | | reset | IntegrationStatus.INITIALIZED |
| IntegrationStatus.RUNNING | Acquisition running. |||
| | | stop | IntegrationStatus.INITIALIZED |
| | | reset | IntegrationStatus.INITIALIZED |
| IntegrationStatus.DETECTOR_STOPPED | Waiting for backend and writer to finish. |||
| | | stop | IntegrationStatus.INITIALIZED |
| | | reset | IntegrationStatus.INITIALIZED |
| IntegrationStatus.FINISHED | Acquisition completed. |||
| | | reset | IntegrationStatus.INITIALIZED |
| IntegrationStatus.ERROR | Something went wrong. |||
| | | stop | IntegrationStatus.INITIALIZED |
| | | reset | IntegrationStatus.INITIALIZED |

A short summary would be:

- You always need to configure the integration before starting the acquisition.
- You cannot change the configuration while the acquisition is running or there is an error.
- The stop method can be called in every state, but it stop the acquisition only if it is running.
- Whatever happens, you have the reset method that returns you in the initial state.
- When the detector stops sending data, the status is DETECTOR_STOPPED. Call STOP to close the backend and stop the 
writing.
- When the detector stops sending data, the backend and writer have completed, 
the status is FINISHED.

<a id="dia_configuration_parameters"></a>
## DIA configuration parameters

The following are the parameters in the DIA.

<a id="dia_configuration_parameters_detector"></a>
### Detector configuration
The mandatory attributes for the detector configuration are:

- *"period"*: Period of time (in seconds) for each frame.
- *"frames"*: Number of frames to acquire.
- *"dr"*: Dynamic range - number of bits (16, 32 etc.)
- *"exptime"* - Exposure time.

In addition, any attribute that the detector supports can be passed here. Please refer to the detector manual for a 
complete list and explanation of the attributes.

An example of a valid detector config:
```json
{
  "period": 0.1,
  "frames": 1000,
  "dr": 16,
  "exptime": 0.0001
}
```

<a id="dia_configuration_parameters_backend"></a>
### Backend configuration
Available and at the same time mandatory backend attributes:

- *"bit_depth"*: Dynamic range - number of bits (16, 32 etc.)
- *"n_frames"*: Number of frames per acquisition.
- *"preview_modulo"*: Modulo to use for the stream preview.
- *"preview_modulo_offset"*: Offset to apply to the frame number before the modulo.

**Warning**: Please note that this 2 attributes must match the information you provided to the detector:

- (backend) bit_depth == (detector) dr
- (backend) n_frames == (detector) frames

If this is not the case, the configuration will fail.

An example of a valid detector config:
```json
{
  "bit_depth": 16,
  "n_frames": 1000
}
```

<a id="dia_configuration_parameters_writer"></a>
### Writer configuration
Due to the data format used for the cSAXS acquisition, the writer configuration is quite large. It is divided into 2 
parts:

- Writer related config (config used by the writer itself to write the data to disk)
- cSAXS file format config (config used to write the file in the cSAXS format) - currently there are no cSAXS format specific
attributes.

An example of a valid writer config would be:
```json
{
    "output_file": "/tmp/dia_test.h5",
    "n_frames": 1000, 
    "user_id": 0,
}
```

**Warning**: Please note that this 2 attributes must match the information you provided to the detector:

- (writer) n_frames == (detector) frames

If this is not the case, the configuration will fail.

#### Writer related config
To configure the writer, you must specify:

- *"output\_file"*: Location where the file will be written.
- *"n_frames"*: Number of frames to acquire.
- *"user_id"*: Under which user to run the writer.

In addition to this properties, a valid config must also have the parameters needed for the cSAXS file format.

#### cSAXS file format config

No format fields at the moment.

<a id="deployment_info"></a>
## Deployment information

In this section we will describe the current deployment, server by server.

<a id="deployment_info_28"></a>
## xbl-daq-28 (Backend server)
On xbl-daq-28 we are running the backend server. The backend is listening on address:

- **http://xbl-daq-28:8080**

It is run using a **systemd** service (/etc/systemd/system/dbe.service). 

The services invokes the startup file **/home/dbe/start_dbe.sh**.

The service can be controlled with the following commands (using sudo or root):
- **systemctl start dbe.service** (start the backend)
- **systemctl stop dbe.service** (stop the backend)
- **journalctl -u dbe.service -f** (check the backend logs)

<a id="deployment_info_29"></a>
## xbl-daq-29 (DIA and writer server)
On xbl-daq-29 we are running the detector integration api. The DIA is listening on address:

- **http://xbl-daq-29:10000**

It is run using a **systemd** service (/etc/systemd/system/dia.service). 

The services invokes the startup file **/home/dia/start_dia.sh**.

The service can be controlled with the following commands (using sudo or root):
- **systemctl start dia.service** (start the dia)
- **systemctl stop dia.service** (stop the dia)
- **journalctl -u dia.service -f** (check the dia logs)

### Writer
The writer is spawn on request from the DIA. To do that, DIA uses the startup file **/home/dia/start_writer.sh**.

Each time the writer is spawn, a separate log file is generated in **/var/log/h5_zmq_writer/**.
