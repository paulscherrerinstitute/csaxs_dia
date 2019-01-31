from enum import Enum
from logging import getLogger

from detector_integration_api.utils import ClientDisableWrapper

_logger = getLogger(__name__)


class IntegrationStatus(Enum):
    READY = "ready",
    RUNNING = "running",
    ERROR = "error",
    COMPONENT_NOT_RESPONDING = "component_not_responding"


E_ACCOUNT_USER_ID_RANGE = [10000, 29999]

MANDATORY_WRITER_CONFIG_PARAMETERS = ["n_frames", "user_id", "output_file"]
MANDATORY_BACKEND_CONFIG_PARAMETERS = ["bit_depth"]
MANDATORY_DETECTOR_CONFIG_PARAMETERS = ["period", "frames", "dr", "exptime", "timing", "cycles"]

CSAXS_FORMAT_INPUT_PARAMETERS = {}


def validate_writer_config(configuration):
    if not configuration:
        raise ValueError("Writer configuration cannot be empty.")

    writer_cfg_params = MANDATORY_WRITER_CONFIG_PARAMETERS + list(CSAXS_FORMAT_INPUT_PARAMETERS.keys())

    # Check if all mandatory parameters are present.
    if not all(x in configuration for x in writer_cfg_params):
        missing_parameters = [x for x in writer_cfg_params if x not in configuration]
        raise ValueError("Writer configuration missing mandatory parameters: %s" % missing_parameters)

    unexpected_parameters = [x for x in configuration.keys() if x not in writer_cfg_params]
    if unexpected_parameters:
        _logger.warning("Received unexpected parameters for writer: %s" % unexpected_parameters)

    # Check if all format parameters are of correct type.
    wrong_parameter_types = ""
    for parameter_name, parameter_type in CSAXS_FORMAT_INPUT_PARAMETERS.items():
        if not isinstance(configuration[parameter_name], parameter_type):

            # If the input type is an int, but float is required, convert it.
            if parameter_type == float and isinstance(configuration[parameter_name], int):
                configuration[parameter_name] = float(configuration[parameter_name])
                continue

            wrong_parameter_types += "\tWriter parameter '%s' expected of type '%s', but received of type '%s'.\n" % \
                                     (parameter_name, parameter_type, type(configuration[parameter_name]))

    if wrong_parameter_types:
        raise ValueError("Received parameters of invalid type:\n%s", wrong_parameter_types)

    user_id = configuration["user_id"]
    if user_id < E_ACCOUNT_USER_ID_RANGE[0] or user_id > E_ACCOUNT_USER_ID_RANGE[1]:
        raise ValueError("Provided user_id %d outside of specified range [%d-%d]." % (user_id,
                                                                                      E_ACCOUNT_USER_ID_RANGE[0],
                                                                                      E_ACCOUNT_USER_ID_RANGE[1]))

    # Check if the filename ends with h5.
    if configuration["output_file"][-3:] != ".h5":
        configuration["output_file"] += ".h5"


def validate_backend_config(configuration):
    if not configuration:
        raise ValueError("Backend configuration cannot be empty.")

    if not all(x in configuration for x in MANDATORY_BACKEND_CONFIG_PARAMETERS):
        missing_parameters = [x for x in MANDATORY_BACKEND_CONFIG_PARAMETERS if x not in configuration]
        raise ValueError("Backend configuration missing mandatory parameters: %s" % missing_parameters)

    if configuration.get("n_frames", 0) != 0:
        raise ValueError("The only allowed values for backend config n_frames=0.")


def validate_detector_config(configuration):
    if not configuration:
        raise ValueError("Detector configuration cannot be empty.")

    # TODO: Move to n_frames with new detector client.
    if "n_frames" in configuration:
        configuration['frames'] = configuration["n_frames"]
        del configuration["n_frames"]


    if not all(x in configuration for x in MANDATORY_DETECTOR_CONFIG_PARAMETERS):
        missing_parameters = [x for x in MANDATORY_DETECTOR_CONFIG_PARAMETERS if x not in configuration]
        raise ValueError("Detector configuration missing mandatory parameters: %s" % missing_parameters)


def validate_configs_dependencies(writer_config, backend_config, detector_config):
    if backend_config["bit_depth"] != detector_config["dr"]:
        raise ValueError("Invalid config. Backend 'bit_depth' set to '%s', but detector 'dr' set to '%s'."
                         " They must be equal."
                         % (backend_config["bit_depth"], detector_config["dr"]))

    # TODO: Move to n_frames with new detector client.
    if detector_config["timing"] == "auto":
        if detector_config["frames"] != writer_config["n_frames"]:
            raise ValueError("Invalid config for timing auto. "
                             "Detector 'n_frames' set to '%s', but writer 'n_frames' set to '%s'."
                             " They must be equal."
                             % (detector_config["n_frames"], writer_config["n_frames"]))

    elif detector_config["timing"] == "trigger":
        if detector_config["cycles"] != writer_config["n_frames"]:
            raise ValueError("Invalid config for timing trigger. "
                             "Detector 'cycles' set to '%s', but writer 'n_frames' set to '%s'."
                             " They must be equal."
                             % (detector_config["cycles"], writer_config["n_frames"]))

    else:
        raise ValueError("Unexpected detector timing config '%s'. Use 'timing' or 'auto'." % detector_config["timing"])


def interpret_status(statuses):
    _logger.debug("Interpreting statuses: %s", statuses)

    writer = statuses["writer"]

    def cmp(status, expected_value):

        _logger.debug("Comparing status '%s' with expected status '%s'.", status, expected_value)

        if status == ClientDisableWrapper.STATUS_DISABLED:
            return True

        if isinstance(expected_value, (tuple, list)):
            return status in expected_value
        else:
            return status == expected_value

    # If no other conditions match.
    interpreted_status = IntegrationStatus.ERROR

    if cmp(writer, "stopped"):
        interpreted_status = IntegrationStatus.READY

    elif cmp(writer, ("receiving", "writing")):
        interpreted_status = IntegrationStatus.RUNNING

    return interpreted_status
