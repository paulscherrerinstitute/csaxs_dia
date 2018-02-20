import json
import os


def get_valid_config():

    filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "csaxs_eiger_config.json")
    with open(filename) as input_file:
        configuration = json.load(input_file)

    return configuration
