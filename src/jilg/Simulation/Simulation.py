import datetime
import itertools
import threading
import traceback
from copy import deepcopy, copy
from threading import Thread

import numpy as np
from PySide6.QtCore import QDateTime

from src.jilg.Main.ModelAnalyser import ModelAnalyser
from src.jilg.Model.MilpSolver import MilpSolver
from src.jilg.Model.Model import Model
from src.jilg.Other.Global import VariableTypes
from src.jilg.Simulation.Event import Event
from src.jilg.Simulation.EventLog import EventLog
from src.jilg.Simulation.SimulationConfiguration import SimulationConfiguration
from src.jilg.Simulation.Trace import Trace
from scipy.stats import truncnorm

from src.jilg.Simulation.ValueGenerator import ValueGenerator


class DiscreteVariableValue:
    name: str
    var_type: VariableTypes
    values: list
    intervals: list
    interval_values: list
    combined_values: list  # (type, value) or  (type, value, interval_value) type==true => value

    def __init__(self, name, var_type):
        self.name = name
        self.var_type = var_type
        self.values = []
        self.intervals = []
        self.interval_values = []
        self.combined_values = []

    def combine_values_and_intervals(self):
        for value in self.values:
            self.combined_values.append((self.name, False, value))
        for interval, interval_value in zip(self.intervals, self.interval_values):
            self.combined_values.append((self.name, True, interval, interval_value))


class Simulation:
    model: Model
    config: SimulationConfiguration
    event_logs: list
    current_event_log: EventLog
    rng: np.random.default_rng
    unused_trace_names: list
    used_trace_name_count: dict
    current_time: datetime.datetime
    sim_thread: Thread
    thread_status_lock: threading.Lock
    number_of_event_logs: int
    event_log_name: str
    event_log_creator: str
    value_generator: ValueGenerator
    possible_traces: (
        int, list, list, bool)  # number_of_possible_traces, valid_ending_traces, other_traces, loop
    thread_status: list
    thread_stop: bool
    exit_with_errors: bool
    errors: str

    def __init__(self, model, config, rng, number_of_event_logs, event_log_name="log",
                 event_log_creator="undefined"):
        self.event_logs = []
        self.event_log_name = event_log_name
        self.event_log_creator = event_log_creator
        self.number_of_event_logs = number_of_event_logs
        self.current_event_log = EventLog(event_log_name, event_log_creator)
        self.model = model
        self.config = config
        self.rng = rng
        self.used_trace_name_count = {}
        self.current_time = self.config.timestamp_anchor
        t = self.current_time
        sgtTimeDelta = datetime.timedelta(hours=self.config.utc_offset)
        sgtTZObject = datetime.timezone(sgtTimeDelta, name="SGT")
        self.current_time = datetime.datetime(t.year, t.month, t.day, t.hour, t.minute, t.second, 0,
                                              sgtTZObject)
        np.random.seed(int(self.rng.uniform(0, 1000)))
        self.thread_status_lock = threading.Lock()
        self.value_generator = ValueGenerator(model, self.rng)
        self.thread_status = []
        self.exit_with_errors = False
        self.errors = ""

    def set_up_sim(self):
        self.unused_trace_names = copy(self.config.trace_names)
        self.used_trace_name_count = {}
        self.current_time = self.config.timestamp_anchor
        t = self.current_time
        sgtTimeDelta = datetime.timedelta(hours=self.config.utc_offset)
        sgtTZObject = datetime.timezone(sgtTimeDelta, name="SGT")
        self.current_time = datetime.datetime(t.year, t.month, t.day, t.hour, t.minute, t.second, 0,
                                              sgtTZObject)
        for trace_name in self.unused_trace_names:
            self.used_trace_name_count[trace_name] = 0
        self.model.reset()
        self.model.generate_initial_values(self.value_generator)

    def run(self):
        try:
            self.set_up_sim()
            self.thread_stop = False
            self.exit_with_errors = False
            self.errors = ""
            if self.config.sim_strategy == "random":
                sim_thread = threading.Thread(target=self.run_random_trace_generation, daemon=True)
                with self.thread_status_lock:
                    self.thread_status = [0, 0, False]
                    # nr_of_current_logs
                    # nr_of_current_traces
                    # sim_ended
                sim_thread.start()
            elif self.config.sim_strategy == "random_exploration":
                self.config.max_trace_duplicates = 0
                #self.config.duplicates_with_data_perspective = False
                self.config.model_has_no_increasing_loop = True
                if self.config.perform_trace_estimation:
                    self.thread_status = [0, 0, False, -1, False]
                else:
                    self.thread_status = [0, 0, False, 0, True]
                    # nr_of_current_logs
                    # nr_of_current_traces
                    # sim_ended
                    # possible_traces_estimation
                    # trace_estimation_finished
                sim_thread = threading.Thread(target=self.run_random_exploration, daemon=True)
                sim_thread.start()
            else:
                self.config.max_trace_duplicates = 0
                self.config.perform_trace_estimation = True
                self.config.duplicates_with_data_perspective = False
                self.config.model_has_no_increasing_loop = True
                self.thread_status = [0, 0, False, -1, False]
                sim_thread = threading.Thread(target=self.run_full_exploration, daemon=True)
                sim_thread.start()
                pass
        except:
            self.exit_with_errors = True
            self.errors = str(traceback.format_exc())

    def calculate_possible_traces(self, model):
        model_copy = deepcopy(model)
        valid_traces = []
        other_traces = []
        partial_traces = []
        self.recursive_trace_estimation(valid_traces, other_traces, partial_traces, model_copy, [],
                                        [], [], [])
        self.thread_status[4] = True
        if self.config.include_partial_traces:
            return len(valid_traces) + len(other_traces) + len(partial_traces), valid_traces, \
                   other_traces, partial_traces
        else:
            return len(valid_traces) + len(other_traces), valid_traces, other_traces

    def recursive_trace_estimation(self, valid_traces, other_traces, partial_traces, model,
                                   current_trace, current_trace_seen_markings,
                                   all_seen_traces_markings, current_no_invisible_trace):
        if self.config.include_invisible_transitions_in_log:
            current_trace_length = len(current_trace)
        else:
            current_trace_length = len(current_no_invisible_trace)
        if not current_trace_length > self.config.max_trace_length:
            if self.thread_stop:
                self.thread_status[0] = len(self.event_logs)
                self.thread_status[1] = 0
                self.thread_status[2] = True
            else:
                if self.config.only_ending_traces:
                    nr_of_traces = len(valid_traces)
                else:
                    nr_of_traces = len(valid_traces) + len(other_traces)
                    if self.config.include_partial_traces:
                        nr_of_traces += len(partial_traces)
                if nr_of_traces < self.config.number_of_traces:
                    with self.thread_status_lock:
                        self.thread_status[3] = nr_of_traces
                    if model.is_in_final_state():
                        if current_trace_length >= self.config.min_trace_length:
                            valid_traces.append(current_trace[:])
                    else:
                        if self.max_loop_iterations_exceeded(current_trace_seen_markings,
                                                             current_trace):
                            if current_trace_length >= self.config.min_trace_length:
                                other_traces.append(current_trace[:])
                        else:
                            enabled_transitions = model.get_enabled_transitions(False, False)
                            if not enabled_transitions:
                                if current_trace_length >= self.config.min_trace_length:
                                    other_traces.append(current_trace[:])
                            else:
                                if self.config.include_partial_traces:
                                    if current_trace:
                                        if current_trace_length >= self.config.min_trace_length:
                                            partial_traces.append(current_trace[:])
                                for transition in enabled_transitions:
                                    model_copy = deepcopy(model)
                                    model_copy.fire_transition(transition.id, False)
                                    current_marking = model_copy.current_marking.to_min_string()
                                    trace_copy = current_trace[:]
                                    trace_copy.append(transition.id)
                                    markings_copy = current_trace_seen_markings[:]
                                    markings_copy.append(current_marking)
                                    if self.config.duplicates_with_invisible_trans:
                                        self.recursive_trace_estimation(valid_traces, other_traces,
                                                                        partial_traces, model_copy,
                                                                        trace_copy,
                                                                        markings_copy,
                                                                        [],
                                                                        [])
                                    else:
                                        no_invisible_trace_copy = current_no_invisible_trace[:]
                                        if not transition.invisible:
                                            no_invisible_trace_copy.append(transition.id)
                                        if (current_marking, current_no_invisible_trace) \
                                                not in all_seen_traces_markings:
                                            all_seen_traces_markings.append(
                                                (current_marking[:], current_no_invisible_trace[:]))
                                            self.recursive_trace_estimation(valid_traces,
                                                                            other_traces,
                                                                            partial_traces,
                                                                            model_copy,
                                                                            trace_copy,
                                                                            markings_copy,
                                                                            all_seen_traces_markings
                                                                            ,
                                                                            no_invisible_trace_copy)

    def run_random_trace_generation(self):
        try:
            break_var = False
            while len(self.event_logs) < self.number_of_event_logs:
                if break_var:
                    break
                while len(self.current_event_log.traces) < self.config.number_of_traces:
                    if break_var:
                        break
                    time_before_trace = copy(self.current_time)
                    success = False
                    trace, reached_valid_final_marking = self.generate_random_single_trace()
                    trace.add_trace_variables(self.model)
                    if not self.config.only_ending_traces or reached_valid_final_marking:
                        if self.count_duplicates(trace) <= self.config.max_trace_duplicates:
                            if self.get_trace_length(trace) >= self.config.min_trace_length:
                                self.current_event_log.traces.append(trace)
                                success = True
                    if not success:
                        self.current_time = time_before_trace
                    self.model.reset()
                    self.model.generate_initial_values(self.value_generator)
                    if self.config.fixed_timestamp:
                        self.current_time = self.config.timestamp_anchor
                    with self.thread_status_lock:
                        self.thread_status[0] = len(self.event_logs)
                        self.thread_status[1] = len(self.current_event_log.traces)
                        self.thread_status[2] = False
                    with self.thread_status_lock:
                        if self.thread_stop:
                            break_var = True
                with self.thread_status_lock:
                    if self.thread_stop:
                        self.thread_status[0] = len(self.event_logs)
                        self.thread_status[1] = 0
                        self.thread_status[2] = True
                        break_var = True
                    self.model.reset()
                    self.model.generate_initial_values(self.value_generator)
                    self.event_logs.append(self.current_event_log)
                    if not break_var:
                        self.current_event_log = EventLog(self.event_log_name,
                                                          self.event_log_creator)
                        self.model.reset()
                        self.model.generate_initial_values(self.value_generator)
                        self.set_up_sim()
            with self.thread_status_lock:
                self.thread_status[0] = len(self.event_logs)
                if break_var:
                    nr_of_traces = 0
                    for log in self.event_logs:
                        nr_of_traces += len(log.traces)
                    self.thread_status[1] = nr_of_traces
                else:
                    self.thread_status[1] = len(self.current_event_log.traces)
                self.thread_status[2] = True
        except:
            self.exit_with_errors = True
            self.errors = str(traceback.format_exc())

    def get_trace_length(self, trace):
        length = 0
        for event in trace.events:
            invis = self.model.get_place_or_transition_by_id(event.trans_id).invisible
            if invis:
                if self.config.include_invisible_transitions_in_log:
                    length += 1
            else:
                length += 1
        return length

    def run_random_exploration(self):
        self.current_event_log = EventLog(self.event_log_name,
                                          self.event_log_creator)
        try:
            if self.config.perform_trace_estimation:
                self.possible_traces = self.calculate_possible_traces(self.model)
                if self.config.only_ending_traces:
                    nr_of_possible_traces = len(self.possible_traces[1])
                else:
                    nr_of_possible_traces = self.possible_traces[0]
            else:
                nr_of_possible_traces = 0
            with self.thread_status_lock:
                self.thread_status = [0, 0, False, nr_of_possible_traces, True]
            while len(self.current_event_log.traces) < nr_of_possible_traces or \
                    not self.config.perform_trace_estimation:
                time_before_trace = copy(self.current_time)
                success = False
                trace, reached_valid_final_marking = self.generate_random_single_trace()
                trace.add_trace_variables(self.model)
                if not self.config.only_ending_traces or reached_valid_final_marking:
                    if self.count_duplicates(trace) <= self.config.max_trace_duplicates:
                        if self.get_trace_length(trace) >= self.config.min_trace_length:
                            self.current_event_log.traces.append(trace)
                            success = True
                if not success:
                    self.current_time = time_before_trace
                if self.config.include_partial_traces:
                    partial_traces = self.determine_partial_traces(trace)
                    if partial_traces:
                        for partial_trace in partial_traces:
                            if self.count_duplicates(
                                    partial_trace) <= self.config.max_trace_duplicates:
                                if len(self.current_event_log.traces) < self.config.number_of_traces:
                                    self.current_event_log.traces.append(partial_trace)
                self.model.reset()
                self.model.generate_initial_values(self.value_generator)
                if self.config.fixed_timestamp:
                    self.current_time = self.config.timestamp_anchor
                with self.thread_status_lock:
                    if self.thread_stop:
                        break
                    elif len(self.current_event_log.traces) >= self.config.number_of_traces:
                        break
                    self.thread_status[0] = len(self.event_logs)
                    self.thread_status[1] = len(self.current_event_log.traces)
                    self.thread_status[2] = False
            with self.thread_status_lock:
                self.model.reset()
                self.model.generate_initial_values(self.value_generator)
                self.event_logs.append(self.current_event_log)
                self.thread_status[0] = len(self.event_logs)
                self.thread_status[1] = len(self.current_event_log.traces)
                self.thread_status[2] = True
        except:
            self.exit_with_errors = True
            self.errors = str(traceback.format_exc())

    def run_full_exploration(self):
        self.current_event_log = EventLog(self.event_log_name,
                                          self.event_log_creator)
        try:
            self.possible_traces = self.calculate_possible_traces(self.model)
            if self.config.only_ending_traces:
                nr_of_possible_traces = len(self.possible_traces[1])
            else:
                nr_of_possible_traces = self.possible_traces[0]
            with self.thread_status_lock:
                self.thread_status = [0, 0, False, nr_of_possible_traces, True]
            variable_values_objs = []
            variable_values = []
            variable_names = []
            analyser = ModelAnalyser()
            interval_dict = analyser.determine_intervals(self.model, None, None, True)
            for variable in self.model.variables:
                variable_values_objs.append(
                    self.determine_discrete_variable_values(variable, interval_dict))
                variable_values_objs[-1].combine_values_and_intervals()
                variable_values.append(variable_values_objs[-1].combined_values)
                variable_names.append(variable.name)
            combinations = list(itertools.product(*variable_values))
            valid_traces = self.possible_traces[1]
            other_traces = self.possible_traces[2]
            variables = self.get_variables()
            milp_solver = MilpSolver()
            traces = valid_traces
            if not self.config.only_ending_traces:
                for trace in other_traces:
                    traces.append(trace)

            break_var = False
            for trace in traces:
                if break_var:
                    break
                with self.thread_status_lock:
                    if self.thread_stop:
                        break
                    elif len(self.current_event_log.traces) >= self.config.number_of_traces:
                        break
                    self.thread_status[0] = len(self.event_logs)
                    self.thread_status[1] = len(self.current_event_log.traces)
                    self.thread_status[2] = False
                guard_strings, written_variables_names = \
                    self.get_guard_strings_and_written_variable(trace)
                if written_variables_names:
                    written_variables = []
                    for variable in variables:
                        if variable.name in written_variables_names:
                            written_variables.append(variable)
                    for combination in combinations:
                        with self.thread_status_lock:
                            if self.thread_stop:
                                break_var = True
                                break
                        success, generated_trace = self.try_combination(trace, combination,
                                                                        guard_strings,
                                                                        written_variables,
                                                                        variables, milp_solver)
                        if success:
                            self.current_event_log.traces.append(generated_trace)
                            partial_traces = self.determine_partial_traces(generated_trace)
                            if partial_traces:
                                for partial_trace in partial_traces:
                                    if self.count_duplicates(
                                            partial_trace) <= self.config.max_trace_duplicates:
                                        if len(self.current_event_log.traces) <\
                                                self.config.number_of_traces:
                                            self.current_event_log.traces.append(partial_trace)
                            break
                else:
                    for variable in self.model.variables:
                        variable.reset()
                    success = True
                    for guard in guard_strings:
                        if not milp_solver.compile_and_evaluate_string(guard, variables):
                            success = False
                            break
                    if success:
                        self.current_event_log.traces.append(
                            self.generate_trace_without_var_writes(trace)
                        )
            with self.thread_status_lock:
                self.model.reset()
                self.model.generate_initial_values(self.value_generator)
                self.event_logs.append(self.current_event_log)
                self.thread_status[0] = len(self.event_logs)
                self.thread_status[1] = len(self.current_event_log.traces)
                self.thread_status[2] = True
        except:
            self.exit_with_errors = True
            self.errors = str(traceback.format_exc())

    def generate_trace_without_var_writes(self, trace):
        if self.config.fixed_timestamp:
            self.current_time = self.config.timestamp_anchor
        transitions = []
        for trans_id in trace:
            transitions.append(self.model.get_place_or_transition_by_id(trans_id))
        for variable in self.model.variables:
            variable.reset()
        generated_trace = Trace(self.generate_trace_name())
        previous_transition = None
        for index, transition in enumerate(transitions):
            try:
                self.current_time += self.forward_time(transition, previous_transition)
            except OverflowError:
                self.current_time = datetime.datetime.max
                event = Event(transition.config.activity_name, self.current_time, self.model,
                              transition.id, self.config.timestamp_millieseconds,
                              transition.invisible)
                generated_trace.events.append(event)
        return generated_trace

    def try_combination(self, trace, combination, guards, written_variables, variables,
                        milp_solver):
        for variable in variables:
            variable.reset()
        for variable in written_variables:
            variable.value = self.get_value_from_combination(combination, variable.name)
            variable.has_current_value = True
            variable.has_been_written_to = True
        success = True
        for guard in guards:
            if not milp_solver.compile_and_evaluate_string(guard, variables):
                success = False
                break
        if success:
            return True, self.generate_trace_with_var_combination(trace, combination)
        else:
            return False, None

    def generate_trace_with_var_combination(self, trace, combination):
        value_gen = ValueGenerator(self.model, self.rng)
        if self.config.fixed_timestamp:
            self.current_time = self.config.timestamp_anchor
        transitions = []
        writes_variable_names = []
        for trans_id in trace:
            transitions.append(self.model.get_place_or_transition_by_id(trans_id))
            for var in transitions[-1].writes_variables:
                writes_variable_names.append(var.name)

        for variable in self.model.variables:
            variable.reset()
        generated_trace = Trace(self.generate_trace_name())
        previous_transition = None
        for index, transition in enumerate(transitions):
            try:
                self.current_time += self.forward_time(transition, previous_transition)
            except OverflowError:
                self.current_time = datetime.datetime.max

            if self.config.values_in_origin_event:
                self.generate_value(transition, combination, value_gen)
                event = Event(transition.config.activity_name, self.current_time, self.model,
                              transition.id, self.config.timestamp_millieseconds,
                              transition.invisible)
                generated_trace.events.append(event)

            else:
                event = Event(transition.config.activity_name, self.current_time, self.model,
                              transition.id, self.config.timestamp_millieseconds,
                              transition.invisible)
                generated_trace.events.append(event)
                self.generate_value(transition, combination, value_gen)

            previous_transition = transition
        return generated_trace

    def generate_value(self, transition, combination, value_gen):
        writes_variables = transition.writes_variables
        for variable in writes_variables:
            combi_value = self.get_discrete_variable_value_by_name(combination,
                                                                   variable.name)
            if combi_value[1]:
                variable.value = self.generate_discrete_variable_interval_value(
                    combi_value[2], variable, value_gen)
            else:
                variable.value = combi_value[2]
            variable.has_been_written_to = True
            variable.has_current_value = True

    def get_value_from_combination(self, combination, var_name):
        for var_value in combination:
            if var_value[0] == var_name:
                if var_value[1]:
                    return var_value[3]
                else:
                    return var_value[2]
        return None

    def get_variables(self):
        variables = []
        for variable in self.model.variables:
            variable.reset()
            variables.append(variable)

        return variables

    def get_guard_strings_and_written_variable(self, trace):
        guard_strings = []
        written_variables = []
        for trans_id in trace:
            trans = self.model.get_place_or_transition_by_id(trans_id)
            written_variables += trans.get_writes_variables_names()
            if trans.guard is not None:
                guard_strings.append(trans.guard.guard_string)
        return guard_strings, written_variables

    def get_discrete_variable_value_by_name(self, combinations, name):
        for combination in combinations:
            if combination[0] == name:
                return combination
        return None

    def determine_discrete_variable_values(self, variable, interval_dict):
        value_gen = ValueGenerator(self.model, self.rng)
        if variable.type == VariableTypes.DOUBLE:
            offset = 0.0000000000000001
        else:
            offset = 1
        var_values = DiscreteVariableValue(variable.name, variable.type)
        analyser = ModelAnalyser()
        var_names = []
        self.config.use_only_values_from_guard_strings = False
        if variable.semantic_information.used_information == 0 and \
                not self.config.use_only_values_from_guard_strings:
            var_values.values = variable.semantic_information.values[0]
        elif variable.semantic_information.used_information == 1 and \
                not self.config.use_only_values_from_guard_strings:
            var_values.intervals = variable.semantic_information.intervals
        else:
            if variable.name in interval_dict.keys():
                var_values.intervals += interval_dict[variable.name]
                var_values.intervals = list(dict.fromkeys(var_values.intervals))

        for var in self.model.variables:
            if var.name != variable.name:
                var_names.append(var.name)
        for trans in self.model.transitions:
            if trans.guard is not None:
                guard_string = trans.guard.guard_string
                for other_variable_name in var_names:
                    guard_string.replace(other_variable_name, "")
                values, values_found = analyser.check_for_values(guard_string, variable.name)
                if values_found:
                    for value in values:
                        if variable.type in [VariableTypes.LONG, VariableTypes.INT]:
                            var_values.values.append(int(value))
                        elif variable.type == VariableTypes.DOUBLE:
                            var_values.values.append(float(value))
                        elif variable.type == VariableTypes.DATE:
                            var_values.values.append(
                                QDateTime.fromString(values, "yyyy-MM-ddThh:mm:ss").
                                    toSecsSinceEpoch())
                        elif variable.type == VariableTypes.BOOL:
                            if value in ["false", "False", "FALSE"]:
                                var_values.values.append(False)
                            else:
                                var_values.values.append(True)
                        else:
                            var_values.values.append(value)

        var_values.values = list(dict.fromkeys(var_values.values))
        if self.config.merge_intervals:
            var_values.intervals = self.check_for_interval_merging(var_values.intervals,
                                                                   offset)
        for interval in var_values.intervals:
            var_values.interval_values.append(
                self.generate_discrete_variable_interval_value(interval,
                                                               variable,
                                                               value_gen))
        return var_values

    def check_for_interval_merging(self, intervals, offset):
        if len(intervals) < 2:
            return intervals
        while True:
            stop = True
            for pair in itertools.product(intervals, repeat=2):
                if pair[0] != pair[1]:
                    success, merged_interval = self.can_merge(pair[0], pair[1], offset)
                    if success:
                        intervals.append(merged_interval)
                        intervals.remove(pair[0])
                        intervals.remove(pair[1])
                        stop = False
                        if len(intervals) < 2:
                            stop = True
                        break
            if stop:
                break
        return intervals

    def can_merge(selv, interval1, interval2, offset):
        op1 = interval1[0]
        op2 = interval2[0]
        v1 = interval1[1]
        v2 = interval2[1]
        if ["<>"] in [op1, op2]:
            return False, None

        elif op1 in ["<=", "<"] and op2 in ["<", "<="]:
            if op1 == "<=" and op2 == "<=":
                return True, ("<=", min(v2, v1))
            elif op1 == "<" and op2 == "<":
                return True, ("<", min(v2, v1))
            elif op1 == "<" and op2 == "<=":
                if v1 == v2:
                    return True, ("<", v1 - offset)
                elif v1 < v2:
                    return True, ("<", v1)
                else:
                    return True, ("<=", v2)
            elif op1 == "<=" and op2 == "<":
                if v1 == v2:
                    return True, ("<", v1 - offset)
                elif v2 < v1:
                    return True, ("<", v2)
                else:
                    return True, ("<=", v1)

        elif op1 in [">=", ">"] and op2 in [">", ">="]:
            if op1 == ">=" and op2 == ">=":
                return True, (">=", max(v2, v1))
            elif op1 == ">" and op2 == ">":
                return True, (">", max(v2, v1))
            elif op1 == ">" and op2 == ">=":
                if v1 == v2:
                    return True, (">", v1 + offset)
                elif v1 > v2:
                    return True, (">", v1)
                else:
                    return True, (">=", v2)
            elif op1 == ">=" and op2 == ">":
                if v1 == v2:
                    return True, (">", v1 + offset)
                elif v2 > v1:
                    return True, (">", v2)
                else:
                    return True, (">=", v1)

        elif op1 == "<" and op2 == ">":
            if v1 - offset > v2 + offset:
                return True, ("<>", v2 + offset, v1 - offset)
            else:
                return False, None

        elif op1 == "<" and op2 == ">=":
            if v1 - offset > v2:
                return True, ("<>", v2, v1 - offset)
            else:
                return False, None

        elif op1 == "<=" and op2 == ">":
            if v1 > v2 + offset:
                return True, ("<>", v1, v2 + offset)
            else:
                return None

        elif op1 == "<=" and op2 == ">=":
            if v1 > v2:
                return True, ("<>", v2, v1)
            else:
                return False, None

        elif op1 == ">" and op2 == "<":
            if v1 - offset < v2 + offset:
                return True, ("<>", v1 + offset, v2 - offset)
            else:
                return False, None

        elif op1 == ">" and op2 == "<=":
            if v2 > v1 + offset:
                return True, ("<>", v1 + offset, v2)
            else:
                return None

        elif op1 == ">=" and op2 == "<":
            if v1 < v2 - offset:
                return True, ("<>", v1, v2 - offset)
            else:
                return False, None

        elif op1 == ">=" and op2 == "<=":
            if v1 < v2:
                return True, ("<>", v1, v2)
            else:
                return False, None
        else:
            return False, None

    def generate_discrete_variable_interval_value(self, interval, variable, value_gen):
        if interval[0] == "<>":
            interval = [interval[1], interval[2]]
        else:
            interval, in_bounds = value_gen.get_merged_constraint_interval([interval], variable)
        if variable.type == VariableTypes.DOUBLE:
            if interval[0] == interval[1]:
                return interval[0]
            return self.rng.uniform(interval[0], interval[1])
        else:
            if interval[0] == interval[1]:
                return interval[0]
            return int(self.rng.uniform(interval[0], interval[1]))

    def determine_partial_traces(self, trace):
        partial_traces = []
        events = trace.events
        if len(events) < 2:
            return partial_traces
        else:
            current_partial_trace = deepcopy(events)
            while len(current_partial_trace) > 1:
                current_partial_trace.pop()
                tmp = Trace(trace.name)
                tmp.events = deepcopy(current_partial_trace)
                if self.get_trace_length(tmp) >= self.config.min_trace_length:
                    partial_traces.append(tmp)
                else:
                    break
            return partial_traces

    def generate_random_single_trace(self):
        trace = Trace(self.generate_trace_name())
        seen_markings = [self.model.current_marking.to_string()]
        previous_transition = None
        while not self.model.is_in_final_state():
            if self.get_trace_length(trace) >= self.config.max_trace_length:
                return trace, False
            elif self.config.model_has_no_increasing_loop and \
                    self.max_loop_iterations_exceeded(seen_markings, trace.get_transition_ids()):
                trace.events.pop()
                return trace, False
            else:
                fired_transition = self.fire_transition()
                if fired_transition is not None:
                    try:
                        self.current_time += self.forward_time(fired_transition,
                                                               previous_transition)
                    except OverflowError:
                        self.current_time = datetime.datetime.max
                    seen_markings.append(self.model.current_marking.to_string())
                    previous_transition = fired_transition
                    if self.config.values_in_origin_event:
                        if fired_transition.writes_variables:
                            self.value_generator.generate_variable_values(fired_transition)
                        self.create_event(fired_transition, trace)
                    else:
                        self.create_event(fired_transition, trace)
                        if fired_transition.writes_variables:
                            self.value_generator.generate_variable_values(fired_transition)
                else:
                    return trace, self.model.is_in_final_state()
        return trace, True

    def generate_trace_name(self):
        if self.config.trace_names:
            if self.config.allow_duplicate_trace_names:
                return self.rng.choice(self.config.trace_names, 1)[0]
            else:
                return self.generate_unique_trace_name()
        else:
            if self.config.allow_duplicate_trace_names:
                return "trace"
            else:
                return "trace" + str(len(self.current_event_log.traces) + 1)

    def generate_unique_trace_name(self):
        if self.unused_trace_names:
            trace_name = self.rng.choice(self.unused_trace_names, 1)[0]
            self.unused_trace_names.remove(trace_name)
            self.used_trace_name_count[trace_name] += 1
            return trace_name + "1"
        else:
            trace_name = self.rng.choice(self.config.trace_names, 1)[0]
            self.used_trace_name_count[trace_name] += 1
            trace_name += str(self.used_trace_name_count[trace_name])
            return trace_name

    def forward_time(self, fired_transition, previous_transition):
        delay = 0
        if previous_transition is not None:
            if not previous_transition.config.no_time_forward:
                delay += self.get_previous_transition_lead_time(previous_transition)

        if not fired_transition.config.no_time_forward:
            if fired_transition.config.use_general_config:
                generator = self.get_truncated_normal(self.config.avg_timestamp_delay,
                                                      self.config.timestamp_delay_sd,
                                                      self.config.timestamp_delay_min,
                                                      self.config.timestamp_delay_max)
                delay += generator.rvs()
            else:
                generator = self.get_truncated_normal(fired_transition.config.avg_time_delay,
                                                      fired_transition.config.time_delay_sd,
                                                      fired_transition.config.time_delay_min,
                                                      fired_transition.config.time_delay_max)
                delay += generator.rvs()
        timedelta = datetime.timedelta(seconds=delay)
        return timedelta

    def get_previous_transition_lead_time(self, previous_transition):
        if previous_transition.config.use_general_config:
            generator = self.get_truncated_normal(self.config.avg_timestamp_lead,
                                                  self.config.timestamp_lead_sd,
                                                  self.config.timestamp_lead_min,
                                                  self.config.timestamp_lead_max)
            return generator.rvs()
        else:
            generator = self.get_truncated_normal(previous_transition.config.avg_lead_time,
                                                  previous_transition.config.lead_time_sd,
                                                  previous_transition.config.lead_time_min,
                                                  previous_transition.config.lead_time_max)
            return generator.rvs()

    def get_truncated_normal(self, mean, sd, low, upp):
        return truncnorm((low - mean) / sd, (upp - mean) / sd, loc=mean, scale=sd)

    def fire_transition(self):
        enabled_transitions, propabilities = self.model.get_enabled_transitions(True, True)
        if len(enabled_transitions) == 0:
            return None
        else:
            chosen_transition = self.rng.choice(enabled_transitions, 1, False, propabilities)[0]
            self.model.fire_transition(chosen_transition.id, True)
            return chosen_transition

    def max_loop_iterations_exceeded(self, seen_markings, trace=[]):
        for marking in seen_markings:
            if seen_markings.count(marking) > self.config.max_loop_iterations:
                return True
        for transition_id in trace:
            if trace.count(transition_id) > self.config.max_loop_iterations_transitions:
                return True
        return False

    def count_duplicates(self, trace):
        duplicate_count = 0
        for other_trace in self.current_event_log.traces:
            if self.are_duplicate_traces(trace, other_trace):
                duplicate_count += 1
        return duplicate_count

    def are_duplicate_traces(self, trace1, trace2):
        consider_invisible_trans = self.config.duplicates_with_invisible_trans
        if not self.equal_trace_length(trace1, trace2, consider_invisible_trans):
            return False
        if not consider_invisible_trans:
            for event1, event2 in zip(self.get_non_invisible_events(trace1),
                                      self.get_non_invisible_events(trace2)):
                if not self.are_duplicate_events(event1, event2):
                    return False
            return True
        else:
            for event1, event2 in zip(trace1.events, trace2.events):
                if not self.are_duplicate_events(event1, event2):
                    return False
            return True

    def equal_trace_length(self, trace1, trace2, consider_invisible_trans):
        if consider_invisible_trans:
            return len(trace1.events) == len(trace2.events)
        else:
            return self.get_trace_length(trace1) == self.get_trace_length(trace2)

    def are_duplicate_events(self, event1, event2):
        if event1.trans_id != event2.trans_id:
            return False
        if self.config.duplicates_with_data_perspective:
            if len(event1.variables) != len(event2.variables):
                return False
            else:
                for variable1, variable2 in zip(sorted(event1.variables),
                                                sorted(event2.variables)):
                    if not self.are_duplicate_variables(variable1, variable2):
                        return False
        return True

    def are_duplicate_variables(self, variable1, variable2):
        if variable1[0] != variable2[0]:
            return False
        elif variable1[1] != variable2[1]:
            return False
        elif variable1[2] != variable2[2]:
            return False
        else:
            return True

    def create_event(self, transition, trace):
        event = Event(transition.config.activity_name, self.current_time, self.model, transition.id,
                      self.config.timestamp_millieseconds, transition.invisible)
        trace.events.append(event)

    def get_non_invisible_events(self, trace):
        events = []
        for event in trace.events:
            if not event.from_invisible_transition:
                events.append(event)
        return events

    def get_trace_length(self, trace):
        event_count = 0
        for event in trace.events:
            if not event.from_invisible_transition:
                event_count += 1
        return event_count


if __name__ == "__main__":
    def can_merge(interval1, interval2, offset):
        op1 = interval1[0]
        op2 = interval2[0]
        v1 = interval1[1]
        v2 = interval2[1]

        if op1 in ["<=", "<"] and op2 in ["<", "<="]:
            return True, ("<", min(v2, v1) - offset)

        elif op1 in [">=", ">"] and op2 in [">", ">="]:
            return True, (">", min(v2, v1) + offset)

        elif op1 == "<" and op2 == ">":
            if v1 - offset > v2 + offset:
                return True, ("<>", v1 - offset, v2 + offset)
            else:
                return False, None

        elif op1 == "<" and op2 == ">=":
            if v1 - offset > v2:
                return True, ("<>", v1 - offset, v2)
            else:
                return False, None

        elif op1 == "<=" and op2 == ">":
            if v1 > v2 + offset:
                return True, ("<>", v2 + offset, v1)
            else:
                return None

        elif op1 == "<=" and op2 == ">=":
            if v1 > v2:
                return True, ("<>", v1, v2)
            else:
                return False, None

        elif op1 == ">" and op2 == "<":
            if v1 - offset < v2 + offset:
                return True, ("<>", v2 - offset, v1 + offset)
            else:
                return False, None

        elif op1 == ">" and op2 == "<=":
            if v2 > v1 + offset:
                return True, ("<>", v1 + offset, v2)
            else:
                return None

        elif op1 == ">=" and op2 == "<":
            if v1 < v2 - offset:
                return True, ("<>", v2 - offset, v1)
            else:
                return False, None

        elif op1 == ">=" and op2 == "<=":
            if v1 < v2:
                return True, ("<>", v2, v1)
            else:
                return False, None
