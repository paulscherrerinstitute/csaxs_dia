[![Build Status](https://travis-ci.org/paulscherrerinstitute/csaxs_dia.svg?branch=master)](https://travis-ci.org/paulscherrerinstitute/csaxs_dia)

# cSAXS Eiger 9M detector integration

The following README is useful for controlling the Eiger 9M deployment at cSAXS.

## Useful info for users

- Preview Address: http://xbl-daq-29:5006/csaxs
- [Eiger Manual](http://slsdetectors.web.psi.ch/docs/pdf/slsDetectorClientDocs.pdf)
- DIA Address: http://xbl-daq-29:10000
- Writer logs: /var/log/h5_zmq_writer/ (on xbl-daq-29)

## DAQ limitations

- **25 Hz MAX operations**. Might loose frames if operated at above this frequency.

## Operation general info:

- In case something goes wrong (restart of backend, acquisition not completed normally etc.) a DIA reset is needed.
- If the backend is not responding (usually due to waiting for lost packets) a backend reset (systemctl) is needed.
After the backend hard reset, a DIA reset is also needed to reconfigure it.
- There might be some delays from the moment you write the file to the moment you are able to see it on the consoles.
This is due to the folder caching done by the file system. To flush the cache you can try:
    - stat FOLDER_OF_FILE
    - touch FOLDER_OF_FILE

## Software installed

The detector integration is made up from the following components:

- Detector integration API (running on xbl-daq-29)
    - https://github.com/datastreaming/detector_integration_api
- Detector client (running on xbl-daq-29)
    - https://github.com/slsdetectorgroup/slsDetectorPackage
- Backend server (running on xbl-daq-28)
    - https://git.psi.ch/HPDI/dafl.psidet
- Writer process (running on xbl-daq-29)
    - https://github.com/paulscherrerinstitute/lib_cpp_h5_writer
- Stream visualizer (running on xbl-daq-29)
    - https://github.com/ivan-usov/streamvis/
    
# Table of content
1. [Quick introduction](#quick)
    1. [Python client](#quick_python)
    2. [Rest API](#quick_rest)
2. [State machine](#state_machine)
3. [DIA configuration parameters](#dia_configuration_parameters)
    1. [Detector configuration](#dia_configuration_parameters_detector)
    2. [Backend configuration](#dia_configuration_parameters_backend)
    3. [Writer configuration](#dia_configuration_parameters_writer)
4. [Preview mode](#dia_preview_mode) 
5. [xbl-daq-28 (Backend server)](#deployment_info_28)
6. [xbl-daq-27 (DIA, writer and preview server)](#deployment_info_27)


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

# This is optional. Restart DIA if you are not sure about its state.
client.reset()

configuration = {
    "backend": {
        "bit_depth": 32, 
        "preview_modulo": 10
    },
    
    "detector": {
        "dr": 32, 
        "frames": 100, 
        "period": 0.04, 
        "exptime": 0.001, 
        "timing": "auto", 
        "cycles": 1
    },
    
    "writer": {
        "n_frames": 100,
        "output_file": "/gpfs/perf/X12SA/Data10/gac-x12saop/tmp/daq_test_32b_100f.h5",
        "user_id": 11057
    }
}

# Start the acquisition.
client.start(parameters=configuration)

# Optional. Get the integration status.
client.get_status()

# Block until the DAQ is ready again (this is optional).
client.wait_for_status("IntegrationStatus.READY")

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
# This is optional. Restart DIA if you are not sure about its state.
curl -X POST http://xbl-daq-29:10000/api/v1/reset

# Write 1000 frames, as user id 11057 (gac-x12saop), to file "/gpfs/perf/X12SA/Data10/gac-x12saop/tmp/dia_test.h5".
curl -X POST http://xbl-daq-29:10000/api/v1/start -H "Content-Type: application/json" -d '
{"backend": {"bit_depth": 16, "preview_modulo": 10},
 "detector": {"dr": 32, "exptime": 0.001, "frames": 100, "period": 0.04, "timing":"auto"},
 "writer": {
  "n_frames": 100,
  "output_file": "/gpfs/perf/X12SA/Data10/gac-x12saop/tmp/daq_test_32b_100f.h5",
  "user_id": 11057
 }
}'

# Get integration status.
curl -X GET http://xbl-daq-29:10000/api/v1/status

# There is no "wait for status" if you are using curl - it is implemented in the Python client.
```

<a id="state_machine"></a>
## State machine

The table below describes the possible states of the integration and the methods that cause a transition 
(this are also the methods that are allowed for a defined state).

Methods that do not modify the state machine are not described in this table, as they can be executed in every state.

| State | State description | Transition method | Next state |
|-------|-------------------|-------------------|------------|
| IntegrationStatus.READY | Integration ready to start. |||
| | | start | IntegrationStatus.RUNNING |
| | | stop | IntegrationStatus.READY |
| | | reset | IntegrationStatus.READY |
| IntegrationStatus.RUNNING | Acquisition started. |||
| | | start | IntegrationStatus.RUNNING |
| | | stop | IntegrationStatus.READY |
| | | reset | IntegrationStatus.READY |
| IntegrationStatus.ERROR | Components in unexpected state. |||
| | | reset | IntegrationStatus.READY |
| IntegrationStatus.COMPONENT_NOT_RESPONSING | Some component is not responding. |||
| | | reset | IntegrationStatus.READY |

A short summary would be:

- During normal operations the DAQ should be in READY or RUNNING state.
- You cannot change the configuration while the acquisition is running or there is an error.
- The reset method can be called in every state, it stops the acquisition and prepared the DAQ for the next one.
- If something unexpected happens, use the RESET method to bring the DAQ to an operational state again.
- When the detector stops sending data, the backend and writer have completed, 
the status is READY again and you can start the next acquisition.

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
- *"cycles"* - Number of cycles to execute.

In addition, any attribute that the detector supports can be passed here. Please refer to the detector manual for a 
complete list and explanation of the attributes:

[Eiger Manual](http://slsdetectors.web.psi.ch/docs/pdf/slsDetectorClientDocs.pdf)

**Warning**: Please note that this attribute must match the information you provided to the detector:

- (backend) bit_depth == (detector) dr
- if (detector) timing == auto
    - (writer) n_frames == (detector) frames
- if (detector) timing == trigger
    - (writer) n_frames == (detector) cycles

An example of a valid detector config:
```json
{
  "period": 0.04,
  "frames": 100,
  "dr": 32,
  "exptime": 0.0001,
  "timing": "auto"
}
```

<a id="dia_configuration_parameters_backend"></a>
### Backend configuration
Available and at the same time mandatory backend attributes:

- *"bit_depth"*: Dynamic range - number of bits (16, 32 etc.)
- *"preview_modulo"*: Modulo to use for the stream preview.
- *"preview_modulo_offset"*: Offset to apply to the frame number before the modulo.
- *"send_every_s"*: Time (in seconds) between frames to be sent to the stream preview.

**Note**: The send_every_s attribute has precedence over the preview_modulo setting. Using both at the same time 
does not make sense and doing so might result in unexpected behaviour.

**Warning**: Please note that this attribute must match the information you provided to the detector:

- (backend) bit_depth == (detector) dr

If this is not the case, the configuration will fail.

An example of a valid backend config:
```json
{
  "bit_depth": 32,
  "preview_modulo": 10,
  "preview_offset": 5
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

**Warning**: Please note that this attribute must match the information you provided to the detector:

- if (detector) timing == auto
    - (writer) n_frames == (detector) frames
- if (detector) timing == trigger
    - (writer) n_frames == (detector) cycles

If this is not the case, the configuration will fail.

#### Writer related config
To configure the writer, you must specify:

- *"output\_file"*: Location where the file will be written.
- *"n_frames"*: Number of frames to acquire.
- *"user_id"*: Under which user to run the writer.

In addition to this properties, a valid config must also have the parameters needed for the cSAXS file format 
(No parameters currently).

#### cSAXS file format config

No format fields at the moment. We use the default SF format.

<a id="dia_preview_mode"></a>
## Preview mode
The preview mode is meant for alignment. You should trigger the detector using timing. You will receive each 
image in the preview web app and the acquisition will be continuously running until you call stop.

The preview web app can be accessed on: http://xbl-daq-29:5006/csaxs

To put the detector into preview mode, use the following parameters:

```python
# Import the client.
# Import the client.
from detector_integration_api import DetectorIntegrationClient

# Connect to the Eiger 9M DIA.
client = DetectorIntegrationClient("http://xbl-daq-29:10000")

# This is optional. Restart DIA if you are not sure about its state.
client.reset()

configuration = {
    "backend": {
        "bit_depth": 32, 
        "preview_modulo":1
    },
    
    "detector": {
        "dr": 32, 
        "frames": 1, 
        "period": 0.04, 
        "exptime": 0.001, 
        "timing": "auto", 
        "cycles": 1000
    },
    
    "writer": {
        "n_frames": 1000,
        "output_file": "/gpfs/perf/X12SA/Data10/gac-x12saop/tmp/daq_test_32b_100f.h5",
        "user_id": 11057
    }
}

# Start the acquisition.
client.start(parameters=configuration)

# Stop the acquisition when you have finished the alignment.
client.stop()

```

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
## xbl-daq-29 (DIA, writer and preview server)
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

To open the last writer log file, the 'wlog' alias is added to some account. You can add this alias to your own 
~/.bashrc by adding:

```bash
alias wlog='less /var/log/h5_zmq_writer/$(ls /var/log/h5_zmq_writer/ -tr | tail -n 1)'
```

### Preview
The preview is also running on xbl-daq-29. The previw can be accessed with any web browser on address:

- http://xbl-daq-29:5006/csaxs

It is run using a **systemd** service (/etc/systemd/system/vis.service). 

The services invokes the startup file **/home/vis/start_vis.sh**.

The service can be controlled with the following commands (using sudo or root):
- **systemctl start vis.service** (start the vis)
- **systemctl stop vis.service** (stop the vis)
- **journalctl -u vis.service -f** (check the vis logs)