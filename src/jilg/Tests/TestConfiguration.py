from unittest import TestCase

import numpy as np
from dateutil.parser import parse

from src.jilg.Main.Configuration import Configuration
from src.jilg.Main.PnmlReader import PnmlReader
from src.jilg.Model.Distribution import Distribution
from src.jilg.Other import Global


class TestConfiguration(TestCase):

    def setUp(self):
        self.reader = PnmlReader()
        self.model_path = Global.test_files_path + "test_dpn.pnml"
        self.output_directory = Global.test_files_path + "output/"
        self.model = self.reader.read_pnml(self.model_path)[0]

    def test_all(self):
        self.setUp()
        config = Configuration(np.random.default_rng(1701))
        config.create_basic_configuration(self.model, self.model_path, self.output_directory)
        self.check_basic_config(config, self.model)
        self.edit_config(config)

        config.write_config_file(Global.test_files_path + "test.json")
        self.model = self.reader.read_pnml(self.model_path)[0]
        config = Configuration(np.random.default_rng(1701))
        config.read_config_file(Global.test_files_path + "test.json", self.model)
        self.check_config_after_write_and_read(config)

    def edit_config(self, config):
        config.model_file_path = "test_model_path"
        config.output_directory_path = "test_output_path"
        config.number_of_event_logs = 1996
        config.logs_in_one_file = True
        config.event_log_name = "test_event_log_name"

        sem_info = config.get_sem_info_by_variable_name("variable2")
        sem_info.dependencies.append("(x=1) => (Y = 5)")
        sem_info.dependencies.append("(x=2) => (Y = 5)")
        sem_info.dependencies.append("(x=3) => (Y = 5)")
        sem_info.values[0].append(5)
        sem_info.values[0].append(6)
        sem_info.has_min = True
        sem_info.min = 10
        sem_info.has_max = True
        sem_info.has_sd = True
        sem_info.sd = 5
        sem_info.avg = 15
        sem_info.max = 20
        sem_info.max = 20
        sem_info.max = 20
        sem_info.distribution = Distribution(np.random.default_rng(1701), "truncated_normal",
                                             {"mean": 15, "standard_deviation": 5, "minimum": 10,
                                              "maximum": 20})
        sem_info.has_distribution = True


        config.simulation_config.sim_strategy = "all"
        config.simulation_config.number_of_traces = 2000
        config.simulation_config.max_trace_length = 70
        config.simulation_config.max_loop_iterations = 5
        config.simulation_config.max_trace_duplicates = 10
        config.simulation_config.duplicates_with_data_perspective = True
        config.simulation_config.only_ending_traces = False
        config.simulation_config.timestamp_anchor = parse("2010-12-17T20:01:02.229+02:05")
        config.simulation_config.fixed_timestamp = True
        config.simulation_config.avg_timestamp_delay = 60 * 3
        config.simulation_config.timestamp_delay_sd = 30
        config.simulation_config.timestamp_delay_min = 5
        config.simulation_config.timestamp_delay_max = 35
        config.simulation_config.random_seed = 1996
        config.simulation_config.trace_names = ["traceA", "traceB"]
        config.simulation_config.allow_duplicate_trace_names = False

    def check_basic_config(self, config, model):
        self.assertEqual(self.model_path, config.model_file_path)
        self.assertEqual(self.output_directory, config.output_directory_path)

        sim_config = config.simulation_config
        self.assertEqual(Global.standard_sim_strategy, sim_config.sim_strategy)

        self.assertEqual(Global.standard_number_of_traces, sim_config.number_of_traces)
        self.assertEqual(Global.standard_max_trace_length, sim_config.max_trace_length)
        self.assertEqual(Global.standard_max_loop_iterations, sim_config.max_loop_iterations)
        self.assertEqual(Global.standard_max_trace_duplicates, sim_config.max_trace_duplicates)
        self.assertEqual(Global.standard_duplicates_with_data_perspective, sim_config.duplicates_with_data_perspective)
        self.assertEqual(Global.standard_only_ending_traces, sim_config.only_ending_traces)
        self.assertEqual(Global.standard_timestamp_anchor, sim_config.timestamp_anchor)
        self.assertEqual(Global.standard_fixed_timestamp, sim_config.fixed_timestamp)
        self.assertEqual(Global.standard_avg_timestamp_delay, sim_config.avg_timestamp_delay)
        self.assertEqual(Global.standard_timestamp_delay_sd, sim_config.timestamp_delay_sd)
        self.assertEqual(Global.standard_random_seed, sim_config.random_seed)

        self.assertEqual(len(model.transitions), len(sim_config.transition_configs))
        trans_config = sim_config.transition_configs[0]
        self.assertEqual("n5", trans_config.transition_id)
        self.assertEqual("diagnose", trans_config.activity_name)
        self.assertEqual(1, trans_config.weight)

        self.assertEqual(len(model.variables), len(config.semantic_information))
        sem_info = config.semantic_information[1]
        self.assertEqual("variable2", sem_info.variable_name)
        self.assertEqual(True, sem_info.has_max)
        self.assertEqual(True, sem_info.has_min)
        self.assertEqual(False, sem_info.has_distribution)
        self.assertEqual([[], []], sem_info.values)
        self.assertEqual([], sem_info.dependencies)
        self.assertEqual(1.0, sem_info.min)
        self.assertEqual(100.0, sem_info.max)

        for variable in model.variables:
            self.assertEqual(variable.name, variable.semantic_information.variable_name)

    def check_config_after_write_and_read(self, config):
        sem_info = config.get_sem_info_by_variable_name("variable2")
        self.assertEqual("(x=1) => (Y = 5)", sem_info.dependencies[0])
        self.assertEqual("(x=2) => (Y = 5)", sem_info.dependencies[1])
        self.assertEqual("(x=3) => (Y = 5)", sem_info.dependencies[2])
        self.assertEqual(5, sem_info.values[0][0])
        self.assertEqual(6, sem_info.values[0][1])
        self.assertEqual(True, sem_info.has_min)
        self.assertEqual(10, sem_info.min)
        self.assertEqual(20, sem_info.max)
        self.assertEqual(True, sem_info.has_max)
        distribution = sem_info.distribution
        self.assertEqual("truncated_normal", distribution.distribution_type)
        self.assertEqual(5, distribution.standard_deviation)
        self.assertEqual(10, distribution.minimum)
        self.assertEqual(20, distribution.maximum)
        self.assertEqual(15, distribution.mean)

        sim_config = config.simulation_config

        self.assertEqual("all", sim_config.sim_strategy)
        self.assertEqual(2000, sim_config.number_of_traces)
        self.assertEqual(70, sim_config.max_trace_length)
        self.assertEqual(5, sim_config.max_loop_iterations)
        self.assertEqual(10, sim_config.max_trace_duplicates)
        self.assertEqual(True, sim_config.duplicates_with_data_perspective)
        self.assertEqual(False, sim_config.only_ending_traces)
        self.assertEqual(parse("2010-12-17T20:01:02.229+02:05"), sim_config.timestamp_anchor)
        self.assertEqual(True, sim_config.fixed_timestamp)
        self.assertEqual(60 * 3, sim_config.avg_timestamp_delay)
        self.assertEqual(5, sim_config.timestamp_delay_min)
        self.assertEqual(35, sim_config.timestamp_delay_max)
        self.assertEqual(30, sim_config.timestamp_delay_sd)
        self.assertEqual(["traceA", "traceB"], sim_config.trace_names)
        self.assertEqual(False, sim_config.allow_duplicate_trace_names)
        self.assertEqual(1996, sim_config.random_seed)

        self.assertEqual("test_model_path", config.model_file_path)
        self.assertEqual("test_output_path", config.output_directory_path)
        self.assertEqual(1996, config.number_of_event_logs)
        self.assertEqual(True, config.logs_in_one_file)
        self.assertEqual("test_event_log_name", config.event_log_name)

        for variable in self.model.variables:
            self.assertEqual(variable.name, variable.semantic_information.variable_name)
