import logging
import threading
import time
import traceback

import numpy as np

from src.jilg.Main.Configuration import Configuration
from src.jilg.Main.PnmlReader import PnmlReader
from src.jilg.Main.XesWriter import XesWriter
from src.jilg.Model.Model import Model
from src.jilg.Main.ModelAnalyser import ModelAnalyser
from src.jilg.Other import Global
from src.jilg.Simulation.EventLog import EventLog
from src.jilg.Simulation.Simulation import Simulation, SimStatus


class Main:
    model_path: str
    model: Model
    config: Configuration
    reader: PnmlReader
    writer: XesWriter
    analyser: ModelAnalyser
    event_logs: list
    simulation: Simulation
    rng: np.random.default_rng
    seed: int
    sim_stop: bool
    thread: threading.Thread
    sim_status: SimStatus
    sim_exit_with_errors: bool
    errors: str

    def __init__(self):
        self.reader = PnmlReader()
        self.writer = XesWriter()
        self.analyser = ModelAnalyser()
        self.event_logs = []
        self.sim_status = SimStatus()
        self.sim_exit_with_errors = False
        self.errors = ""

    def initialize_model_and_config(self, output_dir: str = "") -> (bool, list[str]):
        self.model, warnings = self.reader.read_pnml(self.model_path)
        if self.model is None:
            return False, self.reader.errors
        else:
            self.seed = Global.standard_random_seed
            self.rng = np.random.default_rng(self.seed)
            self.config = Configuration(self.rng)
            self.config.create_basic_configuration(self.model, self.model_path, output_dir)
            return True, warnings

    def analyse_model(self):
        try:
            self.analyser.analyse_model(self.model, self.config)
        except:
            Global.log_error(__file__, "ModelAnalyser failed!", traceback)

    def run_simulation(self, write_event_logs: bool, command_line_mode: bool = False, gui_lock: threading.Lock = None):
        self.sim_exit_with_errors = False
        self.errors = ""
        self.rng = np.random.default_rng(self.config.simulation_config.random_seed)
        self.config.rng = self.rng
        self.model.reset()
        self.simulation = Simulation(self.model, self.config.simulation_config, self.rng,
                                     self.config.number_of_event_logs, self.config.event_log_name)
        self.simulation.config = self.config.simulation_config

        if gui_lock is not None:
            with gui_lock:
                self.sim_status = SimStatus()
        else:
            self.sim_status = SimStatus()

        self.simulation.run()

        if command_line_mode:
            self.run_command_line_mode(write_event_logs)
        else:
            self.thread = threading.Thread(target=self.control_simulation_thread, args=[gui_lock],
                                           daemon=True)
            self.sim_stop = False
            self.thread.start()

    def run_command_line_mode(self, write_event_logs: bool):
        try:
            while True:
                time.sleep(1)
                with self.simulation.thread_status_lock:
                    sim_status = self.simulation.sim_status

                print("\nCurrent simulation status:")
                print("    Nr. of current event logs: {logs}".format(
                    logs=str(sim_status.nr_of_current_logs)))
                print("    Nr. of traces of the current event log: {traces}"
                      .format(traces=str(sim_status.nr_of_current_traces)))
                if self.config.simulation_config.sim_strategy in ["random_exploration", "all"]:
                    print("    Possible traces estimation {traces}"
                          .format(traces=str(sim_status.nr_of_estimated_traces)))
                if sim_status.simulation_ended:
                    break

            self.event_logs = self.simulation.event_logs
            if len(self.event_logs) > 1:
                msg = "\nSimulation finished!\n\n{logs} event logs with a total number of {traces}" \
                      " traces have been generated! \n\nWriting event logs to:\n {dir}"
            else:
                msg = "\nSimulation finished!\n\n{logs} event log with a total number of {traces}" \
                      " traces has been generated! \n\nWriting event logs to:\n {dir}"
            print(msg.format(dir=self.config.output_directory_path, logs=len(self.event_logs),
                          traces=len(self.event_logs[0].traces) * len(self.event_logs)))
            if write_event_logs:
                self.write_event_logs(self.simulation.event_logs)
            if len(self.event_logs) > 1:
                print("\nThe event logs have been written to output directory!")
            else:
                print("\nThe event log has been written to output directory!")

        except KeyboardInterrupt:
            print("\nKeyboard Interrupt! Aborting simulation! Please wait!")
            with self.simulation.thread_status_lock:
                self.simulation.thread_stop = True
            time.sleep(3)
            with self.simulation.thread_status_lock:
                self.event_logs = self.simulation.event_logs
            if write_event_logs and self.event_logs:
                print("\nWriting event log/traces that have been generated so far to {dir}."
                      .format(dir=self.config.output_directory_path))
                self.write_event_logs(self.simulation.event_logs)
                print("\nUnfinished event logs written to output directory!")

        except:
            print("\nThe following exception occurred during the simulation!")
            print(traceback.format_exc())
            self.event_logs = self.simulation.event_logs
            if write_event_logs and self.event_logs:
                print("\nWriting even log/traces that have been generated so far to {dir}."
                      .format(dir=self.config.output_directory_path))
                self.write_event_logs(self.simulation.event_logs)
                print("\nUnfinished event logs written to output directory!")

    def control_simulation_thread(self, gui_lock: threading.Lock):
        try:
            while True:
                time.sleep(0.1)
                with self.simulation.thread_status_lock:
                    status = self.simulation.sim_status
                    if self.simulation.exit_with_errors:
                        raise Exception
                with gui_lock:
                    self.sim_status = status
                    if self.sim_stop:
                        with self.simulation.thread_status_lock:
                            self.simulation.thread_stop = True
                if status.simulation_ended:
                    break
            if not self.sim_stop:
                self.event_logs = self.simulation.event_logs
                threading.Thread(target=self.write_event_logs, args=[self.event_logs],
                                 daemon=False).start()
                with self.simulation.thread_status_lock:
                    self.sim_stop = True
            else:
                with gui_lock:
                    with self.simulation.thread_status_lock:
                        self.sim_status = self.simulation.sim_status
                        self.event_logs = self.simulation.event_logs
        except:
            self.sim_exit_with_errors = True
            self.errors = self.simulation.errors
            self.event_logs = self.simulation.event_logs
            self.event_logs.append(self.simulation.current_event_log)

    def stop_simulation(self) -> bool:
        with self.simulation.thread_status_lock:
            self.sim_stop = True
        if self.simulation.event_logs:
            self.event_logs = self.simulation.event_logs
            return True
        else:
            return False

    def write_event_logs(self, event_logs: [EventLog]):
        self.writer.write_event_logs_to_xes_file(self.config.output_directory_path, event_logs,
                                                 self.config.logs_in_one_file,
                                                 self.config.event_log_name,
                                                 self.config.simulation_config.trace_names,
                                                 self.config.simulation_config
                                                 .include_invisible_transitions_in_log,
                                                 self.config.include_metadata)
