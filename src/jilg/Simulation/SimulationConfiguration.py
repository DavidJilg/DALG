import datetime
from src.jilg.Other.Global import print_summary_global
from src.jilg.Other import Global


class SimulationConfiguration:
    sim_strategy: str
    number_of_traces: int
    max_trace_length: int
    min_trace_length: int
    max_loop_iterations: int
    max_loop_iterations_transitions: int
    max_trace_duplicates: int
    duplicates_with_data_perspective: bool
    only_ending_traces: bool
    include_partial_traces: bool
    timestamp_anchor: datetime.datetime
    utc_offset: int

    fixed_timestamp: bool

    avg_timestamp_delay: int
    timestamp_delay_sd: int
    timestamp_delay_min: int
    timestamp_delay_max: int

    avg_timestamp_lead: int
    timestamp_lead_sd: int
    timestamp_lead_min: int
    timestamp_lead_max: int


    random_seed: int
    transition_configs: list
    trace_names: list
    model_has_no_increasing_loop: bool
    allow_duplicate_trace_names: bool

    values_in_origin_event: bool
    include_invisible_transitions_in_log: bool
    duplicates_with_invisible_trans: bool
    perform_trace_estimation: bool
    merge_intervals: bool

    timestamp_millieseconds: bool

    use_only_values_from_guard_strings: bool

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)

    def __init__(self):
        self.sim_strategy = Global.standard_sim_strategy
        self.number_of_traces = Global.standard_number_of_traces
        self.max_trace_length = Global.standard_max_trace_length
        self.min_trace_length = Global.standard_min_trace_length
        self.max_trace_duplicates = Global.standard_max_trace_duplicates
        self.max_loop_iterations = Global.standard_max_loop_iterations
        self.max_loop_iterations_transitions = Global.standard_max_loop_iterations
        self.duplicates_with_data_perspective = Global.standard_duplicates_with_data_perspective
        self.only_ending_traces = Global.standard_only_ending_traces
        self.timestamp_anchor = Global.standard_timestamp_anchor
        self.utc_offset = Global.standard_utc_offset

        self.fixed_timestamp = Global.standard_fixed_timestamp
        self.avg_timestamp_delay = Global.standard_avg_timestamp_delay
        self.timestamp_delay_min = Global.standard_timestamp_delay_min
        self.timestamp_delay_max = Global.standard_timestamp_delay_max
        self.timestamp_delay_sd = Global.standard_timestamp_delay_sd

        self.avg_timestamp_lead = Global.standard_avg_timestamp_lead
        self.timestamp_lead_min = Global.standard_timestamp_lead_min
        self.timestamp_lead_max = Global.standard_timestamp_lead_max
        self.timestamp_lead_sd = Global.standard_timestamp_lead_sd

        self.model_has_no_increasing_loop = Global.standard_model_has_no_loop
        self.random_seed = Global.standard_random_seed
        self.allow_duplicate_trace_names = Global.standard_allow_duplicate_trace_names
        self.transition_configs = []
        self.trace_names = Global.standard_trace_names
        self.include_partial_traces = Global.standard_include_partial_traces

        self.values_in_origin_event = Global.standard_values_in_origin_event
        self.duplicates_with_invisible_trans = Global.standard_duplicates_with_invisible_trans
        self.include_invisible_transitions_in_log =\
            Global.standard_include_invisible_transitions_in_log

        self.perform_trace_estimation = Global.standard_perform_trace_estimation
        self.use_only_values_from_guard_strings = Global.standard_use_only_values_from_guard_strings
        self.merge_intervals = Global.standard_merge_intervals
        self.timestamp_millieseconds = True



    def get_trans_config_by_id(self, id):
        for trans_config in self.transition_configs:
            if trans_config.transition_id == id:
                return trans_config
        return None
