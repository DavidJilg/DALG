import json
import os

import numpy as np

from src.jilg.Model.Distribution import Distribution
from src.jilg.Other.Global import *
from src.jilg.Model.SemanticInformation import SemanticInformation
from src.jilg.Simulation.SimulationConfiguration import SimulationConfiguration
from src.jilg.Simulation.TransitionConfiguration import TransitionConfiguration

'''
An instance of this class is used to set and access all the configuration options during 
runtime. It, therefore, also contains instances of the SemanticConfiguration, 
TransitionConfiguration, and SimulationConfiguration classed that contain specialized 
configuration options. The class also provides methods to read/write the configuration from/to a 
Json file.
'''


class Configuration:
    model_file_path: str
    output_directory_path: str
    number_of_event_logs: int
    simulation_config: SimulationConfiguration
    semantic_information: list
    logs_in_one_file: bool
    event_log_name: str
    copy_config_to_output_dir: bool
    include_metadata: bool
    rng: np.random.default_rng

    def __init__(self, rng):
        self.semantic_information = []
        self.include_metadata = False
        self.model_file_path = ""
        self.event_log_name = "event_log"
        self.output_directory_path = ""
        self.simulation_config = SimulationConfiguration()
        self.number_of_event_logs = 1
        self.logs_in_one_file = False
        self.rng = rng
        self.copy_config_to_output_dir = True

    def remove_duplicate_variable_values(self):
        for sem_info in self.semantic_information:
            sem_info.remove_value_duplicates()

    def configure_variables_and_transitions(self, model):
        for variable in model.variables:
            for var_config in self.semantic_information:
                if variable.name == var_config.variable_name:
                    variable.semantic_information = var_config
                    if var_config.use_initial_value and not var_config.generate_initial_value:
                        variable.has_initial_value = True
                        variable.initial_value = var_config.use_initial_value
                        variable.value = variable.initial_value
                    if var_config.distribution is not None:
                        variable.has_distribution = True
                    break

        for transition in model.transitions:
            for trans_config in self.simulation_config.transition_configs:
                if transition.id == trans_config.transition_id:
                    transition.config = trans_config
                    transition.invisible = trans_config.invisible
                    break

    def configure_simulation(self, model):
        for transition in model.transitions:
            trans_config_obj = TransitionConfiguration(transition.id)
            trans_config_obj.activity_name = transition.name
            trans_config_obj.invisible = transition.invisible
            self.simulation_config.transition_configs.append(trans_config_obj)

    def create_basic_configuration(self, model, path, output_dir="", nr_of_event_logs=1):
        self.number_of_event_logs = nr_of_event_logs
        self.model_file_path = path
        if output_dir == "":
            self.output_directory_path = os.getcwd() + "/"
        else:
            self.output_directory_path = output_dir
        self.simulation_config = SimulationConfiguration()
        for variable in model.variables:
            for trans_config in self.simulation_config.transition_configs:
                trans_config.included_vars.append(variable.original_name)
            sem_info_obj = SemanticInformation(variable, model)
            if variable.min_value is not None:
                sem_info_obj.has_min = True
                sem_info_obj.min = variable.min_value
            else:
                sem_info_obj.has_min = False
            if variable.max_value is not None:
                sem_info_obj.has_max = True
                sem_info_obj.max = variable.max_value
            else:
                sem_info_obj.has_max = False
            self.semantic_information.append(sem_info_obj)
        self.configure_simulation(model)
        self.configure_variables_and_transitions(model)

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)

    def write_config_file(self, path):
        json_data = {'model_file_path': self.model_file_path,
                     'output_directory': self.output_directory_path,
                     'event_log_name': self.event_log_name,
                     'number_of_event_logs': self.number_of_event_logs,
                     'logs_in_one_file': self.logs_in_one_file,
                     'simulation_config': self.write_simulation_config(),
                     "copy_config_to_output_dir": self.copy_config_to_output_dir,
                     "include_metadata": self.include_metadata,
                     'semantic_information': []}

        for sem_info in self.semantic_information:
            json_data['semantic_information'].append(self.write_semantic_information(sem_info))

        with open(path, 'w') as config_file:
            json.dump(json_data, config_file, indent=3)

    def write_simulation_config(self):
        if self.simulation_config is not None:
            sim_confic_dict = {'sim_strategy': self.simulation_config.sim_strategy,
                               'number_of_traces': self.simulation_config.number_of_traces,
                               'max_trace_length': self.simulation_config.max_trace_length,
                               'min_trace_length': self.simulation_config.min_trace_length,
                               'max_loop_iterations_markings': self.simulation_config.max_loop_iterations,
                               'max_loop_iterations_transitions': self.simulation_config
                                   .max_loop_iterations_transitions,
                               'max_trace_duplicates': self.simulation_config.max_trace_duplicates,
                               'duplicates_with_data': self.simulation_config.duplicates_with_data_perspective,
                               'only_ending_traces': self.simulation_config.only_ending_traces,
                               'timestamp_anchor':
                                   str(self.simulation_config.timestamp_anchor).replace(" ", "T"),
                               'fixed_timestamp': self.simulation_config.fixed_timestamp,
                               'avg_timestamp_delay': self.simulation_config.avg_timestamp_delay,
                               'timestamp_delay_sd': self.simulation_config.timestamp_delay_sd,
                               'timestamp_delay_min': self.simulation_config.timestamp_delay_min,
                               'timestamp_delay_max': self.simulation_config.timestamp_delay_max,
                               'avg_timestamp_lead': self.simulation_config.avg_timestamp_lead,
                               'timestamp_lead_sd': self.simulation_config.timestamp_lead_sd,
                               'timestamp_lead_min': self.simulation_config.timestamp_lead_min,
                               'timestamp_lead_max': self.simulation_config.timestamp_lead_max,

                               'time_intervals': self.simulation_config.time_intervals,
                               'add_time_interval_variance': self.simulation_config.add_time_interval_variance,
                               'max_time_interval_variance': self.simulation_config.max_time_interval_variance,

                               'random_seed': self.simulation_config.random_seed,
                               'transition_configs': [],
                               'trace_names': self.simulation_config.trace_names,
                               'allow_duplicate_trace_names':
                                   self.simulation_config.allow_duplicate_trace_names,
                               'model_has_no_increasing_loop': self.simulation_config.
                                   model_has_no_increasing_loop,
                               'include_partial_traces': self.simulation_config.
                                   include_partial_traces,
                               "values_in_origin_event":
                                   self.simulation_config.values_in_origin_event,
                               "utc_offset": self.simulation_config.utc_offset,
                               "include_invisible_transitions_in_log":
                                   self.simulation_config.include_invisible_transitions_in_log,
                               "duplicates_with_invisible_transitions":
                                   self.simulation_config.duplicates_with_invisible_trans,
                               "perform_trace_estimation":
                                   self.simulation_config.perform_trace_estimation,
                               "merge_intervals": self.simulation_config.merge_intervals,
                               "use_only_values_from_guard_strings":
                                   self.simulation_config.use_only_values_from_guard_strings,
                               "timestamp_millieseconds": self.simulation_config.
                                   timestamp_millieseconds
                               }

            for transition_config in self.simulation_config.transition_configs:
                sim_confic_dict['transition_configs'].append(
                    self.write_transition_config(transition_config))
            return sim_confic_dict
        else:
            return "None"

    def write_transition_config(self, transition_config):
        trans_config_dict = {'transition_id': transition_config.transition_id,
                             'activity_name': transition_config.activity_name,
                             'weight': transition_config.weight,
                             'use_general_config': transition_config.use_general_config,
                             'avg_lead_time': transition_config.avg_lead_time,
                             'lead_time_sd': transition_config.lead_time_sd,
                             'lead_time_min': transition_config.lead_time_min,
                             'lead_time_max': transition_config.lead_time_max,
                             'avg_time_delay': transition_config.avg_time_delay,
                             'time_delay_sd': transition_config.time_delay_sd,
                             'time_delay_min': transition_config.time_delay_min,
                             'time_delay_max': transition_config.time_delay_max,
                             'invisible': transition_config.invisible,
                             'included_vars': transition_config.included_vars,
                             'no_time_forward': transition_config.no_time_forward,
                             'time_intervals': transition_config.time_intervals,
                             'add_time_interval_variance': transition_config.add_time_interval_variance,
                             'max_time_interval_variance': transition_config.max_time_interval_variance}

        return trans_config_dict

    def write_semantic_information(self, sem_info):
        sem_info_dict = {"variable_name": sem_info.variable_name,
                         "variable_original_name": sem_info.original_variable_name,
                         "has_distribution": sem_info.has_distribution, "has_min": sem_info.has_min,
                         "has_max": sem_info.has_max, "dependencies": [], "values": [],
                         "intervals": [], "used_information": sem_info.used_information,
                         "use_initial_value": sem_info.use_initial_value,
                         "initial_value": sem_info.initial_value,
                         'include_inverse_intervals':
                             sem_info.include_inverse_intervals,
                         "precision": sem_info.precision,
                         "has_sd": sem_info.has_sd,
                         "has_avg": sem_info.has_avg,
                         "generate_initial_value": sem_info.generate_initial_value,
                         "fixed_variable": sem_info.fixed_variable,
                         "trace_variable": sem_info.trace_variable,
                         "self_reference_deviation": sem_info.self_reference_deviation
                         }
        if sem_info.has_min:
            sem_info_dict["min"] = sem_info.min
        if sem_info.has_max:
            sem_info_dict["max"] = sem_info.max
        if sem_info.has_sd:
            sem_info_dict["sd"] = sem_info.sd
        if sem_info.has_avg:
            sem_info_dict["avg"] = sem_info.avg

        if sem_info.has_distribution:
            sem_info_dict["distribution"] = self.write_distribution(sem_info)
            sem_info_dict["has_distribution"] = True
        else:
            sem_info_dict["has_distribution"] = False

        for dependency in sem_info.dependencies:
            sem_info_dict["dependencies"].append(dependency)

        for value in sem_info.values:
            sem_info_dict["values"].append(value)

        for interval in sem_info.intervals:
            sem_info_dict["intervals"].append(interval)

        return sem_info_dict

    def write_distribution(self, sem_info):
        distribution = sem_info.distribution
        distribution_dict = {"type": distribution.distribution_type}

        if sem_info.has_sd:
            distribution_dict["standard_deviation"] = sem_info.sd
        if sem_info.has_avg:
            distribution_dict["mean"] = sem_info.avg
        if sem_info.has_min:
            distribution_dict["minimum"] = sem_info.min
        if sem_info.has_max:
            distribution_dict["maximum"] = sem_info.max

        return distribution_dict

    def read_config_file(self, path, model, with_model=True):
        with open(path) as config_file:
            json_data = json.load(config_file)
            self.model_file_path = json_data["model_file_path"]
            self.output_directory_path = json_data["output_directory"]
            if "include_metadata" in json_data.keys():
                self.include_metadata = json_data["include_metadata"]

            self.event_log_name = json_data["event_log_name"]
            self.number_of_event_logs = json_data["number_of_event_logs"]
            if "logs_in_one_file" in json_data.keys():
                self.logs_in_one_file = json_data["logs_in_one_file"]

            sim_config_dict = json_data["simulation_config"]
            self.simulation_config = self.read_simulation_config(sim_config_dict)
            self.semantic_information = []

            self.copy_config_to_output_dir = json_data["copy_config_to_output_dir"]
            for sem_info in json_data['semantic_information']:
                self.semantic_information.append(self.read_sem_info(sem_info, model))
        if with_model:
            self.configure_variables_and_transitions(model)

    def read_simulation_config(self, sim_config_dict):
        sim_config = SimulationConfiguration()
        sim_config.sim_strategy = sim_config_dict['sim_strategy']

        sim_config.number_of_traces = sim_config_dict["number_of_traces"]
        sim_config.max_trace_length = sim_config_dict["max_trace_length"]
        sim_config.min_trace_length = sim_config_dict["min_trace_length"]
        sim_config.max_loop_iterations = sim_config_dict["max_loop_iterations_markings"]
        sim_config.max_loop_iterations_transitions = sim_config_dict["max_loop_iterations" \
                                                                     "_transitions"]
        sim_config.max_trace_duplicates = sim_config_dict["max_trace_duplicates"]
        sim_config.duplicates_with_data_perspective = sim_config_dict["duplicates_with_data"]
        sim_config.only_ending_traces = sim_config_dict["only_ending_traces"]
        sim_config.timestamp_anchor = parse(sim_config_dict["timestamp_anchor"])
        sim_config.fixed_timestamp = sim_config_dict["fixed_timestamp"]
        sim_config.avg_timestamp_delay = sim_config_dict["avg_timestamp_delay"]
        sim_config.timestamp_delay_sd = sim_config_dict["timestamp_delay_sd"]
        sim_config.timestamp_delay_min = sim_config_dict["timestamp_delay_min"]
        sim_config.timestamp_delay_max = sim_config_dict["timestamp_delay_max"]
        sim_config.random_seed = sim_config_dict["random_seed"]
        sim_config.transition_configs = []
        sim_config.trace_names = sim_config_dict["trace_names"]
        sim_config.allow_duplicate_trace_names = sim_config_dict["allow_duplicate_trace_names"]
        sim_config.model_has_no_increasing_loop = sim_config_dict["model_has_no_increasing_loop"]
        sim_config.include_partial_traces = sim_config_dict['include_partial_traces']

        sim_config.avg_timestamp_lead = sim_config_dict['avg_timestamp_lead']
        sim_config.timestamp_lead_sd = sim_config_dict['timestamp_lead_sd']
        sim_config.timestamp_lead_min = sim_config_dict['timestamp_lead_min']
        sim_config.timestamp_lead_max = sim_config_dict['timestamp_lead_max']

        if 'time_intervals' in sim_config_dict.keys():
            sim_config.time_intervals = sim_config_dict['time_intervals']
        if 'add_time_interval_variance' in sim_config_dict.keys():
            sim_config.add_time_interval_variance = sim_config_dict['add_time_interval_variance']
        if 'max_time_interval_variance' in sim_config_dict.keys():
            sim_config.max_time_interval_variance = sim_config_dict['max_time_interval_variance']

        sim_config.utc_offset = sim_config_dict["utc_offset"]

        sim_config.values_in_origin_event = sim_config_dict['values_in_origin_event']
        sim_config.include_invisible_transitions_in_log = \
            sim_config_dict['include_invisible_transitions_in_log']

        sim_config.perform_trace_estimation = sim_config_dict["perform_trace_estimation"]

        sim_config.duplicates_with_invisible_trans = \
            sim_config_dict["duplicates_with_invisible_transitions"]

        sim_config.merge_intervals = sim_config_dict["merge_intervals"]

        if "timestamp_millieseconds" in sim_config_dict.keys():
            sim_config.timestamp_millieseconds = sim_config_dict["timestamp_millieseconds"]

        for trans_config in sim_config_dict["transition_configs"]:
            sim_config.transition_configs.append(self.read_trans_config(trans_config))

        return sim_config

    def read_trans_config(self, trans_config_dict):
        trans_config = TransitionConfiguration(trans_config_dict['transition_id'])
        trans_config.activity_name = trans_config_dict["activity_name"]
        trans_config.use_general_config = trans_config_dict["use_general_config"]
        trans_config.invisible = trans_config_dict["invisible"]
        trans_config.weight = trans_config_dict["weight"]
        if "avg_lead_time" in trans_config_dict.keys():
            trans_config.avg_lead_time = trans_config_dict["avg_lead_time"]
            trans_config.has_avg_lead_time = True
        if "lead_time_min" in trans_config_dict.keys():
            trans_config.lead_time_min = trans_config_dict["lead_time_min"]
            trans_config.has_lead_time_min = True
        if "lead_time_max" in trans_config_dict.keys():
            trans_config.lead_time_max = trans_config_dict["lead_time_max"]
            trans_config.has_lead_time_max = True
        if "lead_time_sd" in trans_config_dict.keys():
            trans_config.lead_time_sd = trans_config_dict["lead_time_sd"]
            trans_config.has_lead_time_sd = True
        if "avg_time_delay" in trans_config_dict.keys():
            trans_config.avg_time_delay = trans_config_dict["avg_time_delay"]
            trans_config.has_avg_time_delay = True
        if "time_delay_sd" in trans_config_dict.keys():
            trans_config.time_delay_sd = trans_config_dict["time_delay_sd"]
            trans_config.has_time_delay_sd = True
        if "time_delay_min" in trans_config_dict.keys():
            trans_config.time_delay_min = trans_config_dict["time_delay_min"]
            trans_config.has_time_delay_min = True
        if "time_delay_max" in trans_config_dict.keys():
            trans_config.time_delay_max = trans_config_dict["time_delay_max"]
            trans_config.has_time_delay_max = True
        if "included_vars" in trans_config_dict.keys():
            trans_config.included_vars = trans_config_dict["included_vars"]
        else:
            trans_config.included_vars = []
        if "time_intervals" in trans_config_dict.keys():
            trans_config.time_intervals = trans_config_dict["time_intervals"]
        if "add_time_interval_variance" in trans_config_dict.keys():
            trans_config.add_time_interval_variance = trans_config_dict[
                "add_time_interval_variance"]
        if "max_time_interval_variance" in trans_config_dict.keys():
            trans_config.max_time_interval_variance = trans_config_dict[
                "max_time_interval_variance"]
        if "no_time_forward" in trans_config_dict.keys():
            trans_config.no_time_forward = trans_config_dict["no_time_forward"]

        return trans_config

    def read_sem_info(self, sem_info, model):
        sem_info_obj = SemanticInformation(model.get_variable_by_name(sem_info['variable_name']), model)
        sem_info_obj.precision = sem_info["precision"]
        sem_info_obj.use_initial_value = sem_info["use_initial_value"]
        sem_info_obj.generate_initial_value = sem_info["generate_initial_value"]
        sem_info_obj.include_inverse_intervals = sem_info["include_inverse_intervals"]
        sem_info_obj.initial_value = sem_info["initial_value"]

        sem_info_obj.has_distribution = sem_info['has_distribution']
        sem_info_obj.has_min = sem_info['has_min']
        sem_info_obj.has_max = sem_info['has_max']
        if sem_info_obj.has_min:
            sem_info_obj.min = sem_info['min']
        if sem_info_obj.has_max:
            sem_info_obj.max = sem_info['max']

        sem_info_obj.has_sd = sem_info['has_sd']
        sem_info_obj.has_avg = sem_info['has_avg']
        if sem_info_obj.has_sd:
            sem_info_obj.sd = sem_info['sd']
        if sem_info_obj.has_avg:
            sem_info_obj.avg = sem_info['avg']

        sem_info_obj.dependencies = sem_info["dependencies"]
        sem_info_obj.values = sem_info["values"]
        sem_info_obj.intervals = sem_info["intervals"]
        sem_info_obj.used_information = sem_info["used_information"]

        if "fixed_variable" in sem_info.keys():
            sem_info_obj.fixed_variable = sem_info["fixed_variable"]
        else:
            sem_info_obj.fixed_variable = False

        if "trace_variable" in sem_info.keys():
            sem_info_obj.trace_variable = sem_info["trace_variable"]
        else:
            sem_info_obj.trace_variable = False

        if "self_reference_deviation" in sem_info.keys():
            sem_info_obj.self_reference_deviation = sem_info["self_reference_deviation"]
        else:
            sem_info_obj.self_reference_deviation = 0

        if sem_info_obj.has_distribution:
            sem_info_obj.distribution = self.initialize_distribution(sem_info["distribution"])

        if "variable_original_name" in sem_info.keys():
            sem_info_obj.variable_original_name = sem_info["variable_original_name"]
        else:
            sem_info_obj.variable_original_name = model.get_variable_by_name(sem_info['variable_name'])\
                .original_name

        return sem_info_obj

    def initialize_distribution(self, distribution_dict):
        distribution = Distribution(self.rng, distribution_dict["type"], distribution_dict)
        return distribution

    def get_sem_info_by_variable_name(self, var_name):
        for sem_info in self.semantic_information:
            if sem_info.variable_name == var_name:
                return sem_info
        return None
