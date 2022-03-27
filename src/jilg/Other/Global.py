import datetime
from enum import Enum
from dateutil.parser import parse

import pytz

test_files_path = "E:/Google Drive/MASTER/Semester 4/Implementation/Mather-Thesis-Implementation/" \
                  "test_files/"

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
standard_avg_timestamp_delay = 60 * 10
standard_timestamp_delay_sd = 60
standard_model_has_no_loop = False
standard_timestamp_delay_min = 0
standard_timestamp_delay_max = 10
standard_random_seed = 1701

standard_avg_timestamp_lead = 60 * 3
standard_timestamp_lead_min = 0
standard_timestamp_lead_max = 60 * 6
standard_timestamp_lead_sd = 60 * 3

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
