import datetime
import logging
from enum import Enum
from dateutil.parser import parse

import pytz

DALG_VERSION = "1.5.0"

test_files_path = "../../resources/test_files/"  # relative path from test classes (src/jilg/Tests)

'''
Standard values used on startup of DALG when the user has not yet configured the options.
'''

standard_include_partial_traces = False
standard_sim_strategy = "random"
standard_number_of_traces = 1
standard_max_trace_length = 10
standard_min_trace_length = 1
standard_max_loop_iterations = 3
standard_max_trace_duplicates = 1
standard_allow_duplicate_trace_names = False
standard_duplicates_with_data_perspective = False
standard_only_ending_traces = False
standard_timestamp_anchor = parse(datetime.datetime.now(pytz.utc).isoformat())
standard_utc_offset = 0
standard_fixed_timestamp = False

standard_random_seed = 1701
standard_model_has_no_loop = False

standard_avg_timestamp_delay = 0
standard_timestamp_delay_sd = 1
standard_timestamp_delay_min = 0
standard_timestamp_delay_max = 1

standard_avg_timestamp_lead = 0
standard_timestamp_lead_min = 0
standard_timestamp_lead_max = 1
standard_timestamp_lead_sd = 1

standard_values_in_origin_event = True
standard_include_invisible_transitions_in_log = False
standard_perform_trace_estimation = True
standard_use_only_values_from_guard_strings = True
standard_merge_intervals = True
standard_duplicates_with_invisible_trans = False
standard_precision = 2

standard_trace_names = ["trace"]


class Status(Enum):
    SIM_RUNNING = "sim_running"
    MODEL_LOADED = "model_loaded"
    INITIAL = "initial"
    op = [">", "<", "-", "+", "*", "/", "&&", "||", "==", "!=", "<=", ">="]


class VariableTypes(Enum):
    DATE = "java.util.Date"
    BOOL = "java.lang.Boolean"
    DOUBLE = "java.lang.Double"
    LONG = "java.lang.Long"
    STRING = "java.lang.String"
    INT = "java.lang.Integer"


def log_error(file, msg, tracestack=None):
    try:
        logging.error(format_log(file, msg))
        if tracestack is not None:
            logging.error(format_log(file, tracestack.format_exc()))
    except:
        pass


def format_log(file, msg):
    return f"{get_file(file)}: {msg}"


def get_file(filename):
    if "\\" in filename:
        return filename.split("\\")[-1].replace(".py", "")
    elif "/" in filename:
        return filename.split("/")[-1].replace(".py", "")
    else:
        return filename


def print_summary_global(obj, print_list_elements):
    assigned_attr = []
    for attribute, value in obj.__dict__.items():
        assigned_attr.append(attribute)
        if type(value) == list:
            if print_list_elements:
                print(f"{attribute} = \'{value}\'")
            else:
                print(f"{attribute} = list_lenght: \'{len(value)}\'")
        else:
            print(f"{attribute} = \'{value}\'")
