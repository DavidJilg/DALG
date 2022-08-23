import datetime
from copy import deepcopy, copy
from unittest import TestCase

import numpy as np
import pytz

from src.jilg.Main.Main import Main
from src.jilg.Main.PnmlReader import PnmlReader
from src.jilg.Model.Model import Model
from src.jilg.Model.Transition import Transition
from src.jilg.Other import Global
from src.jilg.Simulation.Event import Event
from src.jilg.Simulation.EventLog import EventLog
from src.jilg.Simulation.Simulation import Simulation, SimStatus
from src.jilg.Simulation.SimulationConfiguration import SimulationConfiguration
from src.jilg.Simulation.Trace import Trace
from src.jilg.Simulation.TransitionConfiguration import TransitionConfiguration


class TestSimulation(TestCase):

    def setUp(self):
        self.main = Main()
        self.sim_config = SimulationConfiguration()
        self.simulation = Simulation(None, self.sim_config, np.random.default_rng(1701), 1)

    def test_all(self):
        self.setUp()
        self.test_is_duplicates()
        self.test_count_duplicates()
        self.test_forward_time()

    def test_is_duplicates(self):
        # Without Data
        timestamp = datetime.datetime.now(pytz.utc)
        trace1 = Trace("trace1")
        trace2 = Trace("trace2")
        self.sim_config.duplicates_with_data_perspective = False
        self.assertTrue(self.simulation.are_duplicate_traces(trace1, trace2))
        trace1.events.append(Event("event2", timestamp, Model("name"), "t2", False))
        self.assertFalse(self.simulation.are_duplicate_traces(trace1, trace2))
        trace2.events.append(Event("event2", timestamp, Model("name"), "t2", False))
        self.assertTrue(self.simulation.are_duplicate_traces(trace1, trace2))
        trace1.events.append(Event("event3", timestamp, Model("name"), "t3", False))
        trace2.events.append(Event("event3b", timestamp, Model("name"), "t3b", False))
        self.assertFalse(self.simulation.are_duplicate_traces(trace1, trace2))

        # With Data
        trace1 = Trace("trace1")
        trace2 = Trace("trace2")
        trace1.events.append(Event("event1", timestamp, Model("name"), "t1", False))
        trace1.events.append(Event("event2", timestamp, Model("name"), "t2", False))
        trace1.events.append(Event("event3", timestamp, Model("name"), "t3", False))
        trace2.events.append(Event("event1", timestamp, Model("name"), "t1", False))
        trace2.events.append(Event("event2", timestamp, Model("name"), "t2", False))
        trace2.events.append(Event("event3", timestamp, Model("name"), "t3", False))
        self.sim_config.duplicates_with_data_perspective = True
        self.assertTrue(self.simulation.are_duplicate_traces(trace1, trace2))

        trace1.events[0].variables.append(("var1", "value1", "string"))
        self.assertFalse(self.simulation.are_duplicate_traces(trace1, trace2))

        trace2.events[0].variables.append(("var1", "value1", "string"))
        self.assertTrue(self.simulation.are_duplicate_traces(trace1, trace2))

        trace1.events[0].variables.append(("var2", "5", "string"))
        self.assertFalse(self.simulation.are_duplicate_traces(trace1, trace2))

        trace2.events[0].variables.append(("var2", 5, "string"))
        self.assertFalse(self.simulation.are_duplicate_traces(trace1, trace2))

        trace2.events[0].variables[-1] = ("var2", 5, "int")
        self.assertFalse(self.simulation.are_duplicate_traces(trace1, trace2))

        trace2.events[0].variables[-1] = ("var2", "5", "string")
        self.assertTrue(self.simulation.are_duplicate_traces(trace1, trace2))

        trace1.events[2].variables.append(("var3", False, "bool"))
        self.assertFalse(self.simulation.are_duplicate_traces(trace1, trace2))

        trace2.events[2].variables.append(("var3", False, "bool"))
        self.assertTrue(self.simulation.are_duplicate_traces(trace1, trace2))

    def test_count_duplicates(self):
        timestamp = datetime.datetime.now(pytz.utc)
        # Without Data
        traceA1 = Trace("trace1")
        traceB1 = Trace("trace2")
        self.sim_config.duplicates_with_data_perspective = False
        traceA1.events = [Event("event1", timestamp, Model("name"), "t1", False),
                          Event("event2", timestamp, Model("name"), "t2", False),
                          Event("event3", timestamp, Model("name"), "t3", False)]

        traceB1.events = [Event("event1", timestamp, Model("name"), "t1", False),
                          Event("event2", timestamp, Model("name"), "t2", False),
                          Event("event4", timestamp, Model("name"), "t4", False)]
        traceA2 = deepcopy(traceA1)
        traceA3 = deepcopy(traceA1)
        traceB2 = deepcopy(traceB1)
        traceB3 = deepcopy(traceB1)
        self.simulation.current_event_log = EventLog("log1", "creator")

        self.simulation.current_event_log.traces = [traceA1]
        self.assertEqual(1, self.simulation.count_duplicates(traceA1))
        self.assertEqual(0, self.simulation.count_duplicates(traceB1))

        self.simulation.current_event_log.traces = [traceA1, traceB1]
        self.assertEqual(1, self.simulation.count_duplicates(traceA1))
        self.assertEqual(1, self.simulation.count_duplicates(traceB1))

        self.simulation.current_event_log.traces = [traceA1, traceA2, traceA3, traceB1, traceB2,
                                                    traceB3]
        self.assertEqual(3, self.simulation.count_duplicates(traceA1))
        self.assertEqual(3, self.simulation.count_duplicates(traceB1))

        # With Data
        self.sim_config.duplicates_with_data_perspective = True
        traceA1.events = [Event("event1", timestamp, Model("name"), "t1", False),
                          Event("event2", timestamp, Model("name"), "t2", False),
                          Event("event3", timestamp, Model("name"), "t3", False)]

        traceB1.events = [Event("event1", timestamp, Model("name"), "t1", False),
                          Event("event2", timestamp, Model("name"), "t2", False),
                          Event("event4", timestamp, Model("name"), "t4", False)]
        traceA1.events[0].variables = [("var1", "value1", "string")]
        traceA1.events[2].variables = [("var1", 5, "int")]
        traceB1.events[1].variables = [("var1", True, "bool")]
        traceB1.events[2].variables = [("var1", 10, "long")]
        traceA2 = deepcopy(traceA1)
        traceA3 = deepcopy(traceA1)
        traceB2 = deepcopy(traceB1)
        traceB3 = deepcopy(traceB1)

        self.simulation.current_event_log.traces = [traceA1]
        self.assertEqual(1, self.simulation.count_duplicates(traceA1))
        self.assertEqual(0, self.simulation.count_duplicates(traceB1))

        self.simulation.current_event_log.traces = [traceA1, traceB1]
        self.assertEqual(1, self.simulation.count_duplicates(traceA1))
        self.assertEqual(1, self.simulation.count_duplicates(traceB1))

        self.simulation.current_event_log.traces = [traceA1, traceA2, traceA3, traceB1, traceB2,
                                                    traceB3]
        self.assertEqual(3, self.simulation.count_duplicates(traceA1))
        self.assertEqual(3, self.simulation.count_duplicates(traceB1))

    def test_max_loop_iterations_exceeded(self):
        seen_markings = ["currentMarking: ('p1', 1), ('p2', 0), ('p3', 0)",
                         "currentMarking: ('p1', 0), ('p2', 1), ('p3', 0)",
                         "currentMarking: ('p1', 0), ('p2', 1), ('p3', 3)"]
        self.simulation.config.max_loop_iterations = 1
        self.assertFalse(self.simulation.max_loop_iterations_exceeded(seen_markings))

        seen_markings.append("currentMarking: ('p1', 1), ('p2', 0), ('p3', 0)")
        self.assertTrue(self.simulation.max_loop_iterations_exceeded(seen_markings))

        self.sim_config.max_loop_iterations = 2
        self.assertFalse(self.simulation.max_loop_iterations_exceeded(seen_markings))

        seen_markings = ["currentMarking: ('p1', 1), ('p2', 0), ('p3', 0)",
                         "currentMarking: ('p1', 0), ('p2', 1), ('p3', 0)",
                         "currentMarking: ('p1', 0), ('p2', 1), ('p3', 3)",
                         "currentMarking: ('p1', 1), ('p2', 0), ('p3', 0)",
                         "currentMarking: ('p1', 0), ('p2', 1), ('p3', 0)",
                         "currentMarking: ('p1', 0), ('p2', 1), ('p3', 3)",
                         "currentMarking: ('p1', 1), ('p2', 0), ('p3', 0)"]
        self.assertTrue(self.simulation.max_loop_iterations_exceeded(seen_markings))
        self.sim_config.max_loop_iterations = 3
        self.assertFalse(self.simulation.max_loop_iterations_exceeded(seen_markings))

    def test_forward_time(self):
        self.setUp()
        transition1 = Transition("t1")
        transition2 = Transition("t2")
        trans_config1 = TransitionConfiguration("t1")
        trans_config2 = TransitionConfiguration("t2")
        transition1.config = trans_config1
        transition2.config = trans_config2

        self.assertEqual("0:00:00.463425",
                         str(self.simulation.forward_time(transition1, transition2)))

        trans_config1.time_delay_min = 5
        trans_config1.time_delay_max = 60 * 5

        self.assertEqual("0:00:01.139591",
                         str(self.simulation.forward_time(transition1, transition2)))

    def test_generate_trace_name(self):
        self.setUp()
        self.simulation.config.allow_duplicate_trace_names = True
        self.simulation.config.trace_names = []

        self.assertEqual("trace", self.simulation.generate_trace_name())
        self.assertEqual("trace", self.simulation.generate_trace_name())

        self.setUp()
        self.simulation.config.allow_duplicate_trace_names = False
        self.simulation.config.trace_names = []

        self.assertEqual("trace1", self.simulation.generate_trace_name())
        self.simulation.current_event_log.traces.append(None)
        self.assertEqual("trace2", self.simulation.generate_trace_name())

        self.setUp()
        self.simulation.config.allow_duplicate_trace_names = True
        self.simulation.config.trace_names = ["traceA", "traceB"]

        self.assertEqual("traceA", self.simulation.generate_trace_name())
        self.assertEqual("traceA", self.simulation.generate_trace_name())
        self.assertEqual("traceB", self.simulation.generate_trace_name())

        self.setUp()
        self.simulation.config.allow_duplicate_trace_names = False
        self.simulation.config.trace_names = ["traceA", "traceB"]
        self.simulation.unused_trace_names = copy(self.simulation.config.trace_names)
        for trace_name in self.simulation.unused_trace_names:
            self.simulation.used_trace_name_count[trace_name] = 0

        self.assertEqual("traceA1", self.simulation.generate_trace_name())
        self.assertEqual("traceB1", self.simulation.generate_trace_name())
        self.assertEqual("traceA2", self.simulation.generate_trace_name())
        self.assertEqual("traceB2", self.simulation.generate_trace_name())
        self.assertEqual("traceB3", self.simulation.generate_trace_name())

        self.assertEqual(2, self.simulation.used_trace_name_count["traceA"])
        self.assertEqual(3, self.simulation.used_trace_name_count["traceB"])

    def test_calculate_possible_traces(self):
        reader = PnmlReader()
        model, errors = reader.read_pnml(Global.test_files_path + "test_dpn.pnml")
        self.simulation.thread_stop = False
        self.simulation.sim_status = SimStatus(nr_estimation_traces=-1)
        self.simulation.config.number_of_traces = 5
        tuple = self.simulation.calculate_possible_traces(model)
        self.assertEqual(2, tuple[0])
        self.assertEqual([["n5", "n6"], ["n5", "n7"]], tuple[1])
        self.assertEqual([], tuple[2])


