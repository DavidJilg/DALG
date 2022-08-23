import datetime
import json
import sys
import threading
import time
import traceback
import webbrowser as wb
from copy import copy

from dateutil.parser import parse
from PySide6.QtCore import Signal, QRunnable, Slot, QThreadPool, QObject, QTime, QDateTime, QFile, \
    QLocale
from PySide6.QtGui import QKeySequence, Qt, QIcon
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QLabel, \
    QVBoxLayout, QLineEdit, QPlainTextEdit, QRadioButton, QSpinBox, \
    QComboBox, QDoubleSpinBox, QDateTimeEdit, QCheckBox, QTimeEdit, QPushButton, \
    QDialogButtonBox, QWidget

from src.jilg.Main.Configuration import Configuration
from src.jilg.Main.Main import Main
from src.jilg.Model.Distribution import Distribution
from src.jilg.Model.SemanticInformation import SemanticInformation
from src.jilg.Model.Transition import Transition
from src.jilg.Other.Global import VariableTypes, print_summary_global
from src.jilg.Model.Variable import Variable
from src.jilg.Other import Global
from src.jilg.Other.Global import Status
from src.jilg.Simulation.Simulation import Weekday, SimStatus
from src.jilg.Simulation.TransitionConfiguration import TransitionConfiguration
from src.jilg.Simulation.ValueGenerator import ValueGenerator
from src.jilg.UI.MainWindow import Ui_MainWindow
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)


class EventLogWriter(QRunnable):
    main: Main

    def __init__(self, main):
        super(EventLogWriter, self).__init__()
        self.main = main

    @Slot()
    def run(self):
        self.main.write_event_logs(self.main.event_logs)


class GuiUpdateInformation:
    sim_status: SimStatus
    sim_percentage: float
    nr_of_total_traces: int
    sim_strategy: str
    errors_occurred: bool
    errors: str

    def __init__(self, sim_status=SimStatus(), sim_percentage=0.0, nr_of_total_traces=0, sim_strategy="", errors="",
                 errors_occurred=False):
        self.sim_status = copy(sim_status)
        self.sim_percentage = sim_percentage
        self.nr_of_total_traces = nr_of_total_traces
        self.sim_strategy = sim_strategy
        self.errors = errors
        self.errors_occurred = errors_occurred

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)


class WorkerSignals(QObject):
    sim_status = Signal(GuiUpdateInformation)


class SimStatusReporter(QRunnable):
    main: Main
    thread_lock: threading.Lock
    signal: WorkerSignals()
    nr_of_traces: int
    nr_of_event_logs: int
    total_traces: int
    sim_stop: bool
    gui: None
    sim_strat: str

    def __init__(self, main, gui):
        super(SimStatusReporter, self).__init__()
        self.main = main
        self.thread_lock = threading.Lock()
        self.signals = WorkerSignals()
        self.nr_of_event_logs = main.config.number_of_event_logs
        self.nr_of_traces = main.config.simulation_config.number_of_traces
        self.total_traces = self.nr_of_traces * self.nr_of_event_logs
        self.sim_stop = False
        self.gui = gui
        self.sim_strat = self.main.config.simulation_config.sim_strategy

    @Slot()
    def run(self):
        self.sim_stop = False
        self.main.run_simulation(True, True,
                                 self.thread_lock)
        while True:
            time.sleep(0.1)
            with self.gui.gui_update_thread_lock:
                if self.gui.sim_stop:
                    self.sim_stop = True
            if self.sim_stop:
                with self.thread_lock:
                    self.main.sim_stop = True
            with self.thread_lock:
                sim_status = self.main.sim_status
                errors_occurred = self.main.sim_exit_with_errors
                errors = self.main.errors
            if errors_occurred:
                self.signals.sim_status.emit(GuiUpdateInformation(errors=errors, errors_occurred=True))
                break
            if sim_status.simulation_ended:
                break
            if self.sim_strat == "random":
                nr_of_current_traces = (sim_status.nr_of_current_logs * self.nr_of_traces) + \
                                       sim_status.nr_of_current_traces
                percentage = 100 * (nr_of_current_traces / self.total_traces)
                if percentage < 1:
                    percentage = 1
                self.signals.sim_status.emit(GuiUpdateInformation(sim_percentage=percentage, sim_status=sim_status,
                                                                  nr_of_total_traces=nr_of_current_traces,
                                                                  sim_strategy=self.sim_strat))
            elif self.sim_strat == "random_exploration" or self.sim_strat == "all":
                nr_of_current_traces = sim_status.nr_of_current_traces
                if not sim_status.trace_estimation_running:
                    percentage = 0
                else:
                    if sim_status.nr_of_estimated_traces != 0:
                        percentage = 100 * (nr_of_current_traces / sim_status.nr_of_estimated_traces)
                    else:
                        percentage = 100 * (nr_of_current_traces /
                                            self.main.config.simulation_config.number_of_traces)
                    if percentage < 1:
                        percentage = 1

                self.signals.sim_status.emit(GuiUpdateInformation(sim_percentage=percentage, sim_status=sim_status,
                                                                  nr_of_total_traces=nr_of_current_traces,
                                                                  sim_strategy=self.sim_strat))

        # Sim ended
        if self.sim_strat == "random":
            if self.sim_stop:
                nr_of_current_traces = sim_status.nr_of_current_traces
            else:
                nr_of_current_traces = (sim_status.nr_of_current_logs * self.nr_of_traces) + \
                                       sim_status.nr_of_estimated_traces
            percentage = 100 * (nr_of_current_traces / self.total_traces)
            if percentage < 1:
                percentage = 1
            self.signals.sim_status.emit(GuiUpdateInformation(sim_percentage=percentage, sim_status=sim_status,
                                                              nr_of_total_traces=nr_of_current_traces,
                                                              sim_strategy=self.sim_strat))
        elif self.sim_strat == "random_exploration" or self.sim_strat == "all":
            nr_of_current_traces = sim_status.nr_of_current_traces
            if not sim_status.trace_estimation_running:
                percentage = 0
            else:
                if sim_status.nr_of_estimated_traces != 0:
                    percentage = 100 * (nr_of_current_traces / sim_status.nr_of_estimated_traces)
                else:
                    percentage = 100 * (nr_of_current_traces /
                                        self.main.config.simulation_config.number_of_traces)
                if percentage < 1:
                    percentage = 1

            self.signals.sim_status.emit(GuiUpdateInformation(sim_percentage=percentage, sim_status=sim_status,
                                                              nr_of_total_traces=nr_of_current_traces,
                                                              sim_strategy=self.sim_strat))


class VariableInput:
    variable: Variable

    def __init__(self, variable, initial_input, min_input, max_input, values_input,
                 dependencies_input, distributions_input, initial_input2, info_used_input,
                 distributions_mean_input, distributions_sd_input, intervals_input,
                 use_initial_value_input, widget, inverse_intervals_input, precision_input,
                 gen_initial_value_input, fixed_variable_input, trace_variable_input,
                 self_deviation_input, self_deviation_input2):
        self.variable = variable
        self.initial_input = initial_input
        self.min_input = min_input
        self.max_input = max_input
        self.values_input = values_input
        self.dependencies_input = dependencies_input
        self.distributions_input = distributions_input
        self.initial_input2 = initial_input2
        self.info_used_input = info_used_input
        self.distributions_mean_input = distributions_mean_input
        self.distributions_sd_input = distributions_sd_input
        self.intervals_input = intervals_input
        self.use_initial_value_input = use_initial_value_input
        self.widget = widget
        self.inverse_intervals_input = inverse_intervals_input
        self.precision_input = precision_input
        self.gen_initial_value_input = gen_initial_value_input
        self.fixed_variable_input = fixed_variable_input
        self.trace_variable_input = trace_variable_input
        self.self_deviation_input = self_deviation_input
        self.self_deviation_input2 = self_deviation_input2


class TransitionInput:
    transition: Transition

    def __init__(self, transition, activity_name_input, weight_input, invisible_input,
                 mean_delay_input, delay_sd_input, delay_min_input, delay_max_input,
                 lead_mean_input, lead_min_input, lead_max_input, lead_sd_input,
                 general_config_input, widget, scroll_area, included_vars, no_time_forwarding_input,
                 variance_input, max_variance_input, time_intervals_input):
        self.transition = transition
        self.activity_name_input = activity_name_input
        self.weight_input = weight_input
        self.invisible_input = invisible_input
        self.mean_delay_input = mean_delay_input
        self.delay_sd_input = delay_sd_input
        self.delay_min_input = delay_min_input
        self.delay_max_input = delay_max_input
        self.lead_min_input = lead_min_input
        self.lead_max_input = lead_max_input
        self.lead_mean_input = lead_mean_input
        self.lead_sd_input = lead_sd_input
        self.general_config_input = general_config_input
        self.widget = widget
        self.scroll_area = scroll_area
        self.included_vars = included_vars
        self.no_time_forwarding_input = no_time_forwarding_input
        self.variance_input = variance_input
        self.max_variance_input = max_variance_input
        self.time_intervals_input = time_intervals_input


class MainGui:
    app: QApplication
    window: MainWindow
    main: Main
    status: Status
    gui_update_thread: threading.Thread
    progressbar_signal: Signal
    threadpool = QThreadPool
    gui_update_thread_lock: threading.Lock()
    variable_inputs: list
    transition_inputs: list
    variable_layout: QVBoxLayout
    transition_layout: QVBoxLayout
    sim_config_layout: QVBoxLayout
    previous_trace_estimation = 0

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        self.window.setLocale(QLocale(QLocale.English))
        self.variable_inputs = []
        self.configure_menu_actions()
        self.configure_scroll_areas()
        self.main = Main()
        self.transition_inputs = []
        self.configure_button_actions()
        self.configure_combo_boxes()
        self.window.show()
        self.status = Status.INITIAL
        self.window.activateWindow()
        self.sim_stop = False
        self.gui_update_thread_lock = threading.Lock()
        self.change_simulation_config_gui()
        self.window.ui.changing_loop_input.stateChanged \
            .connect(self.process_model_has_no_changing_loop_signal)
        self.window.ui.only_ending_traces_input.stateChanged \
            .connect(self.process_only_ending_traces_signal)
        self.window.setFixedSize(self.window.size())
        self.window.setWindowTitle("DALG: The Data Aware Event Log Generator")
        self.window.setWindowIcon(QIcon(os.getcwd() + "/src/resources/img/icon.png"))
        self.window.ui.loaded_model_label.setWordWrap(True)
        self.window.ui.DALG_VERSION.setText("     v" + str(Global.DALG_VERSION))
        self.window.ui.DALG_VERSION.setStyleSheet("font-size: 9pt")
        self.window.ui.duplicates_with_data_input.stateChanged. \
            connect(lambda: self.change_duplicates_with_data())

        self.window.ui.trace_estimation_input.stateChanged. \
            connect(lambda: self.change_perform_trace_estimation())

        self.window.ui.variance_input.stateChanged.connect(lambda: self.change_variance_input())

        self.change_perform_trace_estimation()
        self.change_duplicates_with_data()
        self.change_variance_input()

        self.fix_gui_element_values()

        if os.name != 'nt':
            self.set_up_for_linux()
        self.check_user_preferences()
        sys.exit(self.app.exec())

    def fix_gui_element_values(self):
        self.window.ui.time_delay_minimum_time_input.setTime(QTime(00, 00, 00))
        self.window.ui.time_lead_minimum_time_input.setTime(QTime(00, 00, 00))

    def check_user_preferences(self):
        preference_path = os.getcwd() + "/src/resources/preferences.json"
        preference_path_production = os.getcwd() + "/resources/preferences.json"
        if os.path.isfile(preference_path):
            with open(preference_path, "r") as preference_file:
                preferences = json.load(preference_file)
            if "show_welcome_screen" in preferences.keys():
                if preferences["show_welcome_screen"]:
                    self.show_welcome_screen()
        elif os.path.isfile(preference_path_production):
            with open(preference_path_production, "r") as preference_file:
                preferences = json.load(preference_file)
            if "show_welcome_screen" in preferences.keys():
                if preferences["show_welcome_screen"]:
                    self.show_welcome_screen()
        else:
            self.create_preference_file(preference_path)
            self.show_welcome_screen()

    def show_welcome_screen(self):
        preference_path = os.getcwd() + "/src/resources/preferences.json"
        ui_file_path = os.getcwd() + "/src/resources/QtDesignerFiles/WelcomeScreen.ui"
        ui_file = QFile(ui_file_path)
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        welcome_screen = loader.load(ui_file, self.window)
        welcome_screen.setWindowIcon(QIcon(os.getcwd() + "/src/resources/img/icon.png"))
        welcome_screen.setFixedSize(welcome_screen.size())
        close_button_box = welcome_screen.findChild(QDialogButtonBox, "buttonBox")
        close_button = close_button_box.button(QDialogButtonBox.Close)
        close_button.setText("Close")
        manual_button = welcome_screen.findChild(QPushButton, "open_manual_button")
        manual_button.clicked.connect(self.open_user_manual)
        checkbox = welcome_screen.findChild(QCheckBox, "checkBox")
        checkbox.stateChanged.connect(
            lambda: self.change_show_welcome_screen(not checkbox.isChecked(), preference_path))
        self.change_show_welcome_screen(True, preference_path)
        welcome_screen.exec()

    def change_show_welcome_screen(self, show_welcome_screen, preference_path):
        with open(preference_path, "r") as preference_file:
            preferences = json.load(preference_file)
        preferences["show_welcome_screen"] = show_welcome_screen
        with open(preference_path, 'w') as preference_file:
            json.dump(preferences, preference_file, indent=3)

    def create_preference_file(self, path):
        preferences = {"show_welcome_screen": True}
        with open(path, 'w') as preference_file:
            json.dump(preferences, preference_file, indent=3)

    def set_up_for_linux(self):
        self.window.ui.line_10.setHidden(True)
        self.window.ui.line_11.setHidden(True)
        self.window.ui.line_7.setHidden(True)
        self.window.ui.line_8.setHidden(True)
        self.window.ui.line_9.setHidden(True)

        self.window.ui.line_2.setHidden(True)
        self.window.ui.line_3.setHidden(True)
        self.window.ui.line_4.setHidden(True)
        self.window.ui.line_5.setHidden(True)
        self.window.ui.line_6.setHidden(True)
        ui = self.window.ui
        widgets = [ui.avg_trans_delay, ui.output_dir_label_17, ui.output_dir_label_22,
                   ui.time_delay_maximum,
                   ui.time_delay_maximum_3, ui.time_delay_minimum, ui.time_delay_minimum_3,
                   ui.time_delay_sd,
                   ui.time_delay_sd_3, ui.inlcude_values_in_origin_event_input,
                   ui.output_dir_label_31, ui.include_invisible_transitions]
        for widget in widgets:
            widget.move(widget.x() - 3, widget.y() + 8)
        ui.time_delay_sd_3.move(ui.time_delay_sd_3.x(), ui.time_delay_sd_3.y() - 7)
        ui.time_delay_minimum_3.move(ui.time_delay_minimum_3.x(), ui.time_delay_minimum_3.y() - 7)
        ui.time_delay_maximum_3.move(ui.time_delay_maximum_3.x(), ui.time_delay_maximum_3.y() - 7)

        ui.avg_trans_lead_days_input.move(ui.avg_trans_lead_days_input.x() - 3,
                                          ui.avg_trans_lead_days_input.y())
        ui.avg_trans_lead_time_input.move(ui.avg_trans_lead_time_input.x() - 3,
                                          ui.avg_trans_lead_time_input.y())
        labels = self.window.findChildren(QLabel)
        for label in labels:
            label.move(label.x(), label.y() + 2)
        ui.output_dir_label_31.move(ui.output_dir_label_31.x(), ui.output_dir_label_31.y() - 1)
        ui.general_config.setFixedHeight(180)
        self.app.setStyleSheet("QGroupBox{font-size: 11pt;}"
                               "QLabel{font-size: 11pt;}"
                               "QComboBox{font-size: 10pt;}")

    def update_gui_with_sim_status(self, update_info: GuiUpdateInformation):
        if update_info.errors_occurred:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("An error occured during the simulation. The simulation was aborted!")
            msg.setInformativeText(str(update_info.errors))
            msg.setWindowTitle("Error!")
            msg.setButtonText(1, "Ok")
            msg.exec()
            if "No traces possible" not in update_info.errors:
                ret = QMessageBox.question(self.window, '', "Write unfinished event logs to"
                                                            " output directory?"
                                           .format(x=len(self.main.event_logs)),
                                           QMessageBox.Yes | QMessageBox.No)

                if ret == QMessageBox.Yes:
                    self.window.ui.sim_status_label.setText("Writing Event Logs to {out_dir}"
                                                            .format(out_dir=self.main.config
                                                                    .output_directory_path))
                    worker = EventLogWriter(self.main)
                    self.threadpool = QThreadPool()
                    self.threadpool.start(worker)
                    self.window.ui.sim_status_label.setText("Not Running")
            self.window.ui.start_simulation_button.setEnabled(True)
            self.window.ui.stop_simulation_button.setEnabled(False)
            self.window.ui.progressBar.setValue(0)
            self.window.ui.label_6.setText("0")
            self.window.ui.label_8.setText("0")
            self.window.ui.label_10.setText("0")
            self.window.ui.sim_status_label.setText("Not Running!")
            self.status = Status.MODEL_LOADED
            self.sim_stop = False
            self.reset_everything_after_simulation_exception()
        else:
            if update_info.sim_strategy == "random":
                self.window.ui.progressBar.setValue(update_info.sim_percentage)
                self.window.ui.label_6.setText(str(update_info.sim_status.nr_of_current_logs))
                self.window.ui.label_8.setText(str(update_info.nr_of_total_traces))
            elif update_info.sim_strategy in ["random_exploration", "all"]:
                if not update_info.sim_status.trace_estimation_running:
                    self.window.ui.sim_status_label.setText("Trace estimation running!")
                else:
                    self.window.ui.sim_status_label.setText("Trace generation running!")
                self.window.ui.progressBar.setValue(update_info.sim_percentage)
                self.window.ui.label_6.setText(str(update_info.sim_status.nr_of_current_logs))
                self.window.ui.label_8.setText(str(update_info.nr_of_total_traces))
                try:
                    sim_status5 = int(update_info.sim_status.nr_of_estimated_traces)
                    self.window.ui.label_10.setText(str(sim_status5))
                except:
                    self.window.ui.label_10.setText("0")

            if update_info.sim_status.simulation_ended:
                self.simulation_ended(update_info)

    def reset_everything_after_simulation_exception(self):
        pass

    # def simulation_ended(self, logs, traces, trace_estimation_abort):
    def simulation_ended(self, update_info):
        if update_info.sim_strategy == "random_exploration":
            trace_estimation_abort = not update_info.sim_status.trace_estimation_running
        else:
            trace_estimation_abort = False
        if trace_estimation_abort:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.NoIcon)
            msg.setText("Simulation Aborted!")
            msg.setWindowTitle("Aborted!")
            msg.setButtonText(1, "Ok")
            msg.exec()
            self.window.ui.start_simulation_button.setEnabled(True)
            self.window.ui.stop_simulation_button.setEnabled(False)
            self.window.ui.progressBar.setValue(0)
            self.window.ui.label_6.setText("0")
            self.window.ui.label_8.setText("0")
            self.window.ui.label_10.setText("0")
            self.status = Status.MODEL_LOADED
            self.sim_stop = False
        else:
            if self.sim_stop:
                self.sim_stop = False
                event_logs_generated = self.main.event_logs
                if event_logs_generated:
                    if len(self.main.event_logs) > 1:
                        msg_string = "{x} event logs have been generated.\n" \
                                     " Should they be written to the output directory?"
                    else:
                        msg_string = "{x} event log has been generated.\n" \
                                     " Should it be written to the output directory?"
                    ret = QMessageBox.question(self.window, 'Simulation ended!', msg_string
                                               .format(x=update_info.sim_status.nr_of_current_logs),
                                               QMessageBox.Yes | QMessageBox.No)

                    if ret == QMessageBox.Yes:
                        self.window.ui.sim_status_label.setText("Writing Event Logs to {out_dir}"
                                                                .format(out_dir=self.main.config
                                                                        .output_directory_path))
                        worker = EventLogWriter(self.main)
                        self.threadpool = QThreadPool()
                        self.threadpool.start(worker)
                        self.window.ui.sim_status_label.setText("Not Running")
                    self.window.ui.progressBar.setValue(0)
                    self.window.ui.label_6.setText("0")
                    self.window.ui.label_8.setText("0")

                else:
                    self.window.ui.progressBar.setValue(0)
                    self.window.ui.label_6.setText("0")
                    self.window.ui.label_8.setText("0")
                self.window.ui.label_10.setText("0")
                self.status = Status.MODEL_LOADED
                self.window.ui.start_simulation_button.setEnabled(True)
            else:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.NoIcon)
                msg.setText("Simulation finished!")
                msg.setWindowTitle("Success!")
                if update_info.sim_status.nr_of_current_logs > 1:
                    msg.setInformativeText(
                        "{logs} event logs with a total number of {traces} traces"
                        " were generated!".format(logs=update_info.sim_status.nr_of_current_logs,
                                                  traces=update_info.nr_of_total_traces))
                else:
                    msg.setInformativeText("One event log with {traces} traces was generated!"
                                           .format(traces=update_info.nr_of_total_traces))
                msg.setButtonText(1, "Ok")
                msg.exec()
                self.window.ui.start_simulation_button.setEnabled(True)
                self.window.ui.stop_simulation_button.setEnabled(False)
                self.window.ui.progressBar.setValue(0)
                self.window.ui.label_6.setText("0")
                self.window.ui.label_8.setText("0")
                self.window.ui.label_10.setText("0")
                self.status = Status.MODEL_LOADED
                self.sim_stop = False

    def clean_up_gui(self):
        for var_input in self.variable_inputs:
            var_input.widget.setParent(None)
        self.variable_inputs = []

        for trans_input in self.transition_inputs:
            trans_input.widget.setParent(None)
        self.transition_inputs = []

    def load_pnml(self, file_path=None):
        if file_path is None:
            file_path = QFileDialog.getOpenFileName(self.window, 'Open file', os.getcwd(),
                                                    "PNML files (*.pnml)")[0]
            with_config = False
        else:
            with_config = True

        if file_path:
            try:
                if self.status == Status.MODEL_LOADED:
                    self.clean_up_gui()
                self.main.model_path = file_path
                success, errors = self.main.initialize_model_and_config(
                    "")
                if not success:
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    if with_config:
                        msg.setText("No configuration file or model was loaded since the following"
                                    " errors occured while parsing model!")
                    else:
                        msg.setText("The model could not be loaded due to the following problems! ")
                    msg.setInformativeText(errors[0])
                    msg.setWindowTitle("Error")
                    msg.exec()
                    if with_config:
                        return False
                else:
                    self.window.ui.loaded_model_label.setText(file_path)
                    self.main.config.model_file_path = file_path
                    self.update_gui_and_config()
                    self.main.analyse_model()
                    self.status = Status.MODEL_LOADED
                    self.transition_layout.addWidget(self.window.ui.general_config_2)
                    self.variable_layout.addWidget(self.window.ui.general_config_3)
                    for variable in self.main.model.variables:
                        self.add_variable_input_widget(variable)
                    for transition in self.main.model.transitions:
                        self.add_transition_input_widget(transition)
                    self.update_config_from_gui()
                    if errors:
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.NoIcon)
                        msg.setText("Successfully loaded model but the following problems"
                                    " occurred:")
                        msg.setWindowTitle("Success with Warnings")
                        info_text = ""
                        for warning in errors:
                            info_text += warning + "\n"
                        msg.setInformativeText(info_text)
                        msg.setButtonText(1, "Ok")
                        msg.exec()
                        if with_config:
                            return True
                    else:
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.NoIcon)
                        msg.setText("Successfully loaded model!")
                        msg.setWindowTitle("Success")
                        msg.setButtonText(1, "Ok")
                        msg.exec()
                        if with_config:
                            return True
            except:
                self.display_error_msg(str(traceback.format_exc()),
                                       "An Error occurred while loading the model!")
        if with_config:
            return False

    def configure_menu_actions(self):
        ui = self.window.ui
        ui.actionExit.triggered.connect(lambda: self.app.exit())
        ui.actionLoad_PnmlFile.triggered.connect(lambda: self.load_pnml())
        # ui.actionAbout.triggered.connect(lambda: self.display_about_info())
        ui.actionLoad_Configuration.triggered.connect(lambda: self.load_config())
        ui.actionSafe_Configuration.triggered.connect(lambda: self.safe_config())
        ui.actionExit.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_Q))
        # ui.actionAbout.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_A))
        ui.actionLoad_PnmlFile.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_O))
        ui.actionLoad_Configuration.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_L))
        ui.actionSafe_Configuration.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_S))

        ui.actionOpen_User_Manual.triggered.connect(lambda: self.open_user_manual())
        ui.actionOpen_User_Manual.setShortcut(QKeySequence(Qt.Key_F1))

        ui.actionShow_Welcome_Screen_Again.setShortcut(Qt.Key_F2)

        ui.actionShow_Welcome_Screen_Again.triggered.connect(lambda: self.show_welcome_screen())

    def configure_button_actions(self):
        self.window.ui.set_output_dir_button.clicked.connect(self.set_output_dir)
        self.window.ui.start_simulation_button.clicked.connect(self.start_simulation)
        self.window.ui.stop_simulation_button.clicked.connect(self.stop_simulation)
        self.window.ui.load_model_button.clicked.connect(lambda: self.load_pnml(None))
        self.window.ui.stop_simulation_button.setEnabled(False)

    def stop_simulation(self):
        if self.status.SIM_RUNNING:
            with self.gui_update_thread_lock:
                self.sim_stop = True
            self.window.ui.stop_simulation_button.setEnabled(False)
        else:
            self.window.ui.progressBar.setValue(0)
            self.window.ui.label_6.setText("0")
            self.window.ui.label_8.setText("0")
            self.status = Status.MODEL_LOADED
            self.window.ui.sim_status_label.setText("Not Running")

    def check_override(self):
        path = self.main.config.output_directory_path + self.main.config.event_log_name
        if self.main.config.number_of_event_logs > 1:
            for i in range(self.main.config.number_of_event_logs):
                if os.path.isfile(path + str(i + 1) + ".xes"):
                    return True
            return False
        else:
            return os.path.isfile(path + ".xes")

    def change_decimal_input(self, var_input: VariableInput):
        precision = var_input.precision_input.value()
        var_input.initial_input.setDecimals(precision)
        var_input.max_input.setDecimals(precision)
        var_input.min_input.setDecimals(precision)
        # var_input.distributions_sd_input.setDecimals(precision)
        # var_input.distributions_mean_input.setDecimals(precision)

    def start_simulation(self):
        continue_with_errors = False
        if self.status == Status.MODEL_LOADED:
            config_valid, warnings = self.check_configuration()
            if not config_valid:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                info_text = "The current configuration is invalid! The following problems" \
                            " were found" \
                            " when checking the configuration:\n\n"
                for warning in warnings:
                    info_text += warning + "\n"
                info_text += "\nExceptions could occur if the simulation is started with" \
                             " this configuration. These exceptions can also cause problems" \
                             " that can" \
                             " not be fixed without restarting the program and, therefore," \
                             " could also cause problems for future simulations!" \
                             " \n\nDo you want to continue anyway?"
                ret = QMessageBox.question(self.window, 'Configuration invalid!',
                                           info_text,
                                           QMessageBox.Yes | QMessageBox.No)

                if ret == QMessageBox.Yes:
                    continue_with_errors = True
            if config_valid or continue_with_errors:
                try:
                    self.update_config_from_gui()
                except:
                    self.display_error_msg(str(traceback.format_exc()),
                                           "An Error occurred while trying to parse the"
                                           " configuration!\n"
                                           "The simulation could not be started!")
                    return
                if self.check_override():
                    ret = QMessageBox.question(self.window, '',
                                               "Event log files with the specified name already"
                                               " exist in the output directory. Files will be"
                                               " overwritten! Continue anyway?",
                                               QMessageBox.Yes | QMessageBox.No)

                    if ret == QMessageBox.Yes:
                        if self.main.config.copy_config_to_output_dir:
                            self.safe_config(self.main.config.output_directory_path +
                                             self.main.config.event_log_name + "_config.json", True)
                        worker = SimStatusReporter(self.main, self)
                        self.threadpool = QThreadPool()
                        worker.signals.sim_status.connect(self.update_gui_with_sim_status)
                        self.threadpool.start(worker)
                        self.status = Status.SIM_RUNNING
                        self.window.ui.start_simulation_button.setEnabled(False)
                        self.window.ui.sim_status_label.setText("Running")
                        self.window.ui.stop_simulation_button.setEnabled(True)

                    else:
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.NoIcon)
                        msg.setText("Simulation aborted!")
                        msg.setWindowTitle("Information")
                        msg.setButtonText(1, "Ok")
                        msg.exec()
                else:
                    if self.main.config.copy_config_to_output_dir:
                        self.safe_config(self.main.config.output_directory_path +
                                         self.main.config.event_log_name + "_config.json", True)
                    worker = SimStatusReporter(self.main, self)
                    self.threadpool = QThreadPool()
                    worker.signals.sim_status.connect(self.update_gui_with_sim_status)
                    self.threadpool.start(worker)
                    self.status = Status.SIM_RUNNING
                    self.window.ui.start_simulation_button.setEnabled(False)
                    self.window.ui.sim_status_label.setText("Running")
                    self.window.ui.stop_simulation_button.setEnabled(True)
        elif self.status == Status.SIM_RUNNING:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Simulation already running!")
            msg.setWindowTitle("Error")
            msg.exec()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("No Model Loaded! Click the \"Load Model\" button or use the \"File\""
                        "option in the top left of the menu bar.")
            msg.setWindowTitle("Error")
            msg.exec()

    def check_configuration(self):
        warnings = []
        valid = True
        ui = self.window.ui
        if not ui.output_path_input.text().endswith("/"):
            ui.output_path_input.setText(ui.output_path_input.text() + "/")
        if not os.path.isdir(ui.output_path_input.text()):
            warnings.append("Output directory not valid!")
            valid = False
        if ui.file_name_input.text() == "":
            warnings.append("File name can not be empty!")
            valid = False
        try:
            int(ui.seed_input.text())
        except:
            warnings.append("Random seed must be a positive whole number!")
            valid = False
        min_trace_length = self.window.ui.min_trace_length_input.value()
        max_trace_length = self.window.ui.max_trace_length_input.value()
        if not max_trace_length - min_trace_length > 0:
            warnings.append("Maxmimum trace length must be greater then minimum trace length!")
            valid = False
        trans_delay_min = self.get_seconds_from_days_and_QTimeEdit(
            self.window.ui.time_delay_minimum_days_input,
            self.window.ui.time_delay_minimum_time_input)
        trans_delay_max = self.get_seconds_from_days_and_QTimeEdit(
            self.window.ui.time_delay_maximum_days_input,
            self.window.ui.time_delay_maximum_time_input)
        trans_lead_min = self.get_seconds_from_days_and_QTimeEdit(
            self.window.ui.time_lead_minimum_days_input,
            self.window.ui.time_lead_minimum_time_input)
        trans_lead_max = self.get_seconds_from_days_and_QTimeEdit(
            self.window.ui.time_lead_maximum_days_input,
            self.window.ui.time_lead_maximum_time_input)
        if trans_delay_max - trans_delay_min <= 0:
            valid = False
            warnings.append("(General Transition Delay Max.) - (General Transition Delay Min.)"
                            " must be greater then 0!")
        if trans_lead_max - trans_lead_min <= 0:
            valid = False
            warnings.append("(General Transition Lead Time Max.)"
                            " - (General Transition Lead Time Min.)"
                            " must be greater then 0!")
        try:
            self.parse_time_intervals(self.window.ui.time_intervals_input)
            self.check_time_intervals(self.window.ui.time_intervals_input.toPlainText())
        except Exception:
            warnings.append("Invalid time intervals in general transition configuration!")
            valid = False

        for var_input in self.variable_inputs:
            var_warnings = self.check_variable_config_input(var_input)
            if var_warnings:
                warnings += var_warnings
                valid = False
        for trans_input in self.transition_inputs:
            trans_warnings = self.check_transition_config_input(trans_input)
            if trans_warnings:
                warnings += trans_warnings
                valid = False

        return valid, warnings

    def check_time_intervals(self, text):
        if text != "":
            text = text.replace(" ", "").replace("\n", "")
            if "|" not in text:
                raise Exception
            if "-" not in text:
                raise Exception
            if ";" in text:
                intervals = text.split(";")
                for interval in intervals:
                    self.check_time_interval(interval)
            else:
                self.check_time_interval(text)

    def check_time_interval(self, time_interval):
        weekdays, interval = time_interval.split("|")
        if "," in weekdays:
            weekdays = weekdays.split(",")
        start_string, stop_string = interval.split("-")
        interval_start_time = datetime.datetime.strptime(start_string, "%H:%M:%S")
        interval_stop_time = datetime.datetime.strptime(stop_string, "%H:%M:%S")
        if interval_start_time > interval_stop_time:
            raise Exception
        if not weekdays:
            raise Exception
        for weekday in weekdays:
            Weekday[weekday].value

    def check_variable_config_input(self, var_input: VariableInput):
        warnings = []
        var_type = var_input.variable.type
        var_name = var_input.variable.original_name
        warnings += self.check_values_config(var_input, var_name)
        warnings += self.check_dependencies_config(var_input, var_name)
        if var_type == VariableTypes.STRING:
            if var_input.use_initial_value_input.isChecked() and not var_input.initial_input.text() \
                    and not var_input.gen_initial_value_input.isChecked():
                warnings.append("Initial value field can not be empty if an initial value should be"
                                " used for variable {name}!".format(name=var_name))

        elif var_type in [VariableTypes.INT, VariableTypes.LONG, VariableTypes.DOUBLE]:
            if var_input.info_used_input.currentIndex() in [1, 2]:  # Intervals or Distribution
                if var_input.info_used_input.currentIndex() == 1:
                    warnings += self.check_intervals_config(var_input, var_name)
                min = var_input.min_input.value()
                max = var_input.max_input.value()
                if max - min <= 0:
                    warnings.append("Max - Min is not greater than 0 for variable {name}!"
                                    .format(name=var_name))
            if var_input.info_used_input.currentIndex() == 2 and \
                    var_input.distributions_input.currentIndex() != 0:
                if var_input.distributions_sd_input.value() <= 0:
                    warnings.append("Standard deviation must be greater than 0 for variable {name}!"
                                    .format(name=var_name))
        elif var_type == VariableTypes.DATE:
            if var_input.info_used_input.currentIndex() in [1, 2]:  # Intervals or Distribution
                if var_input.info_used_input.currentIndex() == 1:
                    warnings += self.check_intervals_config(var_input, var_name)
                min = var_input.min_input.dateTime().toSecsSinceEpoch()
                max = var_input.max_input.dateTime().toSecsSinceEpoch()
                if max - min <= 0:
                    warnings.append("Max - Min is not greater than 0 for variable {name}!"
                                    .format(name=var_name))
            if self.get_seconds_from_days_and_QTimeEdit(var_input.distributions_sd_input[0],
                                                        var_input.distributions_sd_input[1]) == 0:
                warnings.append("Standard deviation is not allowed to be 0"
                                " (seconds since epoch time) for variable {name}!"
                                .format(name=var_name))

        return warnings

    def check_values_config(self, var_input: VariableInput, var_name, only_errors=False):
        warnings = []
        try:
            values = self.parse_values(var_input, var_input.variable.type)
            if len(values) != 2:
                raise Exception
            if len(values[0]) != len(values[1]) and values[1] and not only_errors:
                warnings.append("Number of values does not equal number of weights for the"
                                " variable {name}!".format(name=var_name))
                raise Exception
            if var_input.variable.type in [VariableTypes.STRING, VariableTypes.BOOL]:
                used_info = 0
            else:
                used_info = var_input.info_used_input.currentIndex()
            if not values[0] and used_info == 0 and not only_errors:
                warnings.append("No values specified for variable {name} even though it is"
                                " specified that the values should "
                                "be used for the data generation!".format(name=var_name))
        except:
            warnings.append("Could not parse values for variable {name}!".format(name=var_name))
        return warnings

    def check_dependencies_config(self, var_input: VariableInput, var_name, only_exceptions=False):
        warnings = []
        try:
            dependencies = self.parse_dependencies(var_input, var_input.variable.type)
        except:
            warnings.append(
                "Could not parse dependencies for variable {name}!".format(name=var_name))
            dependencies = None
        var_type = var_input.variable.type
        if dependencies is not None and var_type in [VariableTypes.INT, VariableTypes.LONG,
                                                     VariableTypes.DOUBLE,
                                                     VariableTypes.DATE] and not only_exceptions:
            if var_type == VariableTypes.DATE:
                min = var_input.min_input.dateTime().toSecsSinceEpoch()
                max = var_input.max_input.dateTime().toSecsSinceEpoch()
            else:
                min = var_input.min_input.value()
                max = var_input.max_input.value()
            for dependency in dependencies:
                operator = dependency[1][0].replace(" ", "")
                value = dependency[1][1]
                if operator not in ["<", "<=", ">", ">=", "==", "!=", "+", "-", "*", "/"]:
                    warnings.append("Illegal operator '{op}' used for dependency definition of the "
                                    "variable {variable}!".format(op=operator, variable=var_name))
                if operator == "<":
                    if value <= min:
                        warnings.append("Dependency definition for the variable {name} exceeds the "
                                        "defined minimum value!".format(name=var_name))
                elif operator == ">":
                    if value >= max:
                        warnings.append("Dependency definition for the variable {name} exceeds the "
                                        "defined maximum value!".format(name=var_name))
                elif operator == "<=":
                    if value < min:
                        warnings.append("Dependency definition for the variable {name} exceeds the "
                                        "defined minimum value!".format(name=var_name))
                elif operator == ">=":
                    if value > max:
                        warnings.append("Dependency definition for the variable {name} exceeds the "
                                        "defined maximum value!".format(name=var_name))
                elif operator == "==":
                    if value > max:
                        warnings.append("Dependency definition for the variable {name} exceeds the "
                                        "defined maximum value!".format(name=var_name))
                    if value < min:
                        warnings.append("Dependency definition for the variable {name} exceeds the "
                                        "defined minimum value!".format(name=var_name))
        return warnings

    def check_intervals_config(self, var_input: VariableInput, var_name, only_exceptions=False):
        warnings = []
        try:
            intervals = self.parse_intervals(var_input, var_input.variable.type)
        except:
            warnings.append("Could not parse intervals for variable {name}!".format(name=var_name))
            intervals = None
        if intervals is not None and not only_exceptions:
            if len(intervals) < 1:
                warnings.append("No intervals specified for variable {name} even though it is"
                                " specified that intervals should "
                                "be used for the data generation!".format(name=var_name))
            if var_input.variable.type == VariableTypes.DATE:
                min = var_input.min_input.dateTime().toSecsSinceEpoch()
                max = var_input.max_input.dateTime().toSecsSinceEpoch()
            else:
                min = var_input.min_input.value()
                max = var_input.max_input.value()
            for interval in intervals:
                operator = interval[0].replace(" ", "")
                if operator not in ["<", ">", "<=", ">="]:
                    warnings.append("Illegal operator '{op}' used for interval definition or the "
                                    "variable {variable}".format(op=operator, variable=var_name))

                value = interval[1]
                if operator == "<":
                    if value <= min or value == min:
                        warnings.append("Interval definition for the variable {name} is lower than"
                                        " the defined minimum value!".format(name=var_name))
                elif operator == ">":
                    if value >= max or value == max:
                        warnings.append("Interval definition for the variable {name} exceeds the "
                                        "defined maximum value!".format(name=var_name))
                elif operator == "<=":
                    if value < min or value == min:
                        warnings.append("Interval definition for the variable {name} is lower than"
                                        " the defined minimum value!".format(name=var_name))
                elif operator == ">=":
                    if value > max or value == max:
                        warnings.append("Interval definition for the variable {name} exceeds the "
                                        "defined maximum value!".format(name=var_name))
                elif operator == "==":
                    if value > max:
                        warnings.append("Interval definition for the variable {name} exceeds the "
                                        "defined maximum value!".format(name=var_name))
                    if value < min:
                        warnings.append("Interval definition for the variable {name} is lower than"
                                        " the defined minimum value!".format(name=var_name))
            if var_input.inverse_intervals_input.isChecked():
                value_gen = ValueGenerator(None, None)
                rev_intervals = value_gen.get_inverse_intervals(intervals, only_inverse=True)
                for interval in rev_intervals:
                    operator = interval[0]
                    value = interval[1]
                    if operator == "<":
                        if value <= min:
                            warnings.append(
                                "Reverse Interval definition for the variable {name} is lower than"
                                " the defined minimum value!".format(name=var_name))
                    elif operator == ">":
                        if value >= max:
                            warnings.append(
                                "Reverse interval for the variable {name} exceeds the "
                                "defined maximum value!".format(name=var_name))
                    elif operator == "<=":
                        if value < min:
                            warnings.append(
                                "Reverse Interval definition for the variable {name} is lower than"
                                " the defined minimum value!".format(name=var_name))
                    elif operator == ">=":
                        if value > max:
                            warnings.append(
                                "Reverse interval for the variable {name} exceeds the "
                                "defined maximum value!".format(name=var_name))
                    elif operator == "==":
                        if value > max:
                            warnings.append(
                                "Reverse interval for the variable {name} exceeds the "
                                "defined maximum value!".format(name=var_name))
                        if value < min:
                            warnings.append(
                                "Reverse Interval definition for the variable {name} is lower than"
                                " the defined minimum value!".format(name=var_name))

        return warnings

    def check_transition_config_input(self, trans_input: TransitionInput):
        warnings = []
        trans_id = trans_input.transition.id
        if not trans_input.activity_name_input.text():
            warnings.append("Activity name for transition {id} is empty!".format(id=trans_id))
        if not trans_input.general_config_input.isChecked():
            trans_delay_min = self.get_seconds_from_days_and_QTimeEdit(
                trans_input.delay_min_input[0],
                trans_input.delay_min_input[1])
            trans_delay_max = self.get_seconds_from_days_and_QTimeEdit(
                trans_input.delay_max_input[0],
                trans_input.delay_max_input[1])
            trans_lead_min = self.get_seconds_from_days_and_QTimeEdit(
                trans_input.lead_min_input[0],
                trans_input.lead_min_input[1])
            trans_lead_max = self.get_seconds_from_days_and_QTimeEdit(
                trans_input.lead_max_input[0],
                trans_input.lead_max_input[1])
            if trans_delay_max - trans_delay_min <= 0:
                warnings.append("(Transition Delay Max.) - (Transition Delay Min.)"
                                " is not greater then 0 for transition {id}!".format(id=trans_id))
            if trans_lead_max - trans_lead_min <= 0:
                warnings.append("(Transition Lead Time Max.) - (Transition Lead Time Min.)"
                                " is not greater then 0 for transition {id}!".format(id=trans_id))
            try:
                self.parse_time_intervals(trans_input.time_intervals_input)
                self.check_time_intervals(trans_input.time_intervals_input.toPlainText())
            except:
                warnings.append("Invalid time intervals for transition {id}!".format(id=trans_id))
        return warnings

    def update_config_from_gui(self):
        config = self.main.config
        sim_config = config.simulation_config
        ui = self.window.ui
        config.output_directory_path = ui.output_path_input.text()
        config.event_log_name = ui.file_name_input.text()
        config.number_of_event_logs = ui.nr_of_event_logs_input.value()
        config.copy_config_to_output_dir = ui.include_config_input.isChecked()

        config.include_metadata = ui.include_metadata_input.isChecked()

        if config.output_directory_path:
            if not config.output_directory_path.endswith("/"):
                config.output_directory_path += "/"
        sim_strat_index = ui.sim_strategy_input.currentIndex()
        if sim_strat_index == 0:
            sim_config.sim_strategy = "random"
        elif sim_strat_index == 1:
            sim_config.sim_strategy = "random_exploration"
        else:
            sim_config.sim_strategy = "all"
        sim_config.number_of_traces = ui.nr_of_traces_input.value()
        sim_config.max_trace_length = ui.max_trace_length_input.value()
        sim_config.min_trace_length = ui.min_trace_length_input.value()
        sim_config.max_loop_iterations = ui.max_loop_iterations_input.value()
        sim_config.max_loop_iterations_transitions = ui.max_loop_iterations_transitions_input \
            .value()
        sim_config.model_has_no_increasing_loop = ui.changing_loop_input.isChecked()
        sim_config.max_trace_duplicates = ui.max_trace_duplicates_input.value()

        sim_config.duplicates_with_data_perspective = ui.duplicates_with_data_input.isChecked()
        sim_config.only_ending_traces = ui.only_ending_traces_input.isChecked()
        sim_config.include_partial_traces = ui.partial_traces_input.isChecked()

        sim_config.timestamp_anchor = ui.timestamp_anchor_input.dateTime().toPython()
        sim_config.fixed_timestamp = ui.fixed_timestamp_anchor_input.isChecked()

        sim_config.values_in_origin_event = ui.inlcude_values_in_origin_event_input.isChecked()
        sim_config.trace_names = [ui.trace_name_input.text()]

        sim_config.utc_offset = ui.utc_offset_input.value()

        sim_config.perform_trace_estimation = ui.trace_estimation_input.isChecked()

        sim_config.include_invisible_transitions_in_log = \
            ui.include_invisible_transitions_input.isChecked()

        sim_config.duplicates_with_invisible_trans = \
            ui.duplicates_with_invisible_trans_input.isChecked()

        sim_config.merge_intervals = ui.merge_intervals_input.isChecked()
        sim_config.use_only_values_from_guard_strings = ui.limit_variable_values_input.isChecked()

        sim_config.timestamp_millieseconds = ui.timestamp_millieseconds_input.isChecked()

        sim_config.max_time_interval_variance = ui.max_variance_input.value()
        sim_config.add_time_interval_variance = ui.variance_input.isChecked()
        sim_config.time_intervals = self.parse_time_intervals(ui.time_intervals_input)

        if ui.seed_input.text():
            sim_config.random_seed = int(ui.seed_input.text())
        else:
            sim_config.random_seed = Global.standard_random_seed

        self.configure_variables_from_gui()
        self.configure_transitions_from_gui()

    def configure_variables_from_gui(self):
        for var_input in self.variable_inputs:
            self.configure_variable_from_gui(var_input)

    def configure_variable_from_gui(self, var_input: VariableInput):
        variable = var_input.variable
        var_type = variable.type
        var_config = variable.semantic_information

        var_config.use_initial_value = var_input.use_initial_value_input.isChecked()
        var_config.generate_initial_value = var_input.gen_initial_value_input.isChecked()

        var_config.fixed_variable = var_input.fixed_variable_input.isChecked()
        var_config.trace_variable = var_input.trace_variable_input.isChecked()

        if var_type == VariableTypes.BOOL:
            if var_input.initial_input.isChecked():
                var_config.initial_value = False
            else:
                var_config.initial_value = True

            var_config.has_distribution = False
            var_config.has_min = False
            var_config.has_max = False
            var_config.dependencies = self.parse_dependencies(var_input,
                                                              var_type)
            var_config.values = self.parse_values(var_input, var_type)
            var_config.distribution = None
        elif var_type == VariableTypes.INT or var_type == VariableTypes.LONG or var_type \
                == VariableTypes.DOUBLE:
            var_config.include_inverse_intervals = var_input.inverse_intervals_input.isChecked()

            var_config.self_reference_deviation = var_input.self_deviation_input.value()

            var_config.initial_value = var_input.initial_input.value()
            var_config.has_distribution = True
            var_config.has_min = True
            var_config.has_max = True
            var_config.min = var_input.min_input.value()
            var_config.max = var_input.max_input.value()
            var_config.dependencies = self.parse_dependencies(var_input,
                                                              var_type)
            var_config.values = self.parse_values(var_input, var_type)
            var_config.intervals = self.parse_intervals(var_input, var_type)
            var_config.used_information = var_input.info_used_input.currentIndex()
            rng = self.main.rng
            if var_input.distributions_input.currentIndex() == 0:
                distribution_type = "uniform"
            elif var_input.distributions_input.currentIndex() == 1:
                distribution_type = "normal"
            elif var_input.distributions_input.currentIndex() == 2:
                distribution_type = "exponential"
            other_arguments_dict = {"minimum": var_config.min, "maximum": var_config.max,
                                    "mean": var_input.distributions_mean_input.value(),
                                    "standard_deviation": var_input.distributions_sd_input.value()}
            var_config.has_sd = True
            var_config.has_avg = True
            var_config.sd = var_input.distributions_sd_input.value()
            var_config.avg = var_input.distributions_mean_input.value()

            distribution = Distribution(rng, distribution_type, other_arguments_dict)
            var_config.distribution = distribution
            if var_type == VariableTypes.DOUBLE:
                var_config.precision = var_input.precision_input.value()
        elif var_type == VariableTypes.DATE:
            seconds = self.get_seconds_from_days_and_QTimeEdit(var_input.self_deviation_input,
                                                               var_input.self_deviation_input2)
            var_config.self_reference_deviation = seconds

            if var_config.use_initial_value and not var_config.generate_initial_value:
                var_config.initial_value = var_input.initial_input.dateTime().toSecsSinceEpoch()
            else:
                try:
                    var_config.initial_value = var_input.initial_input.dateTime().toSecsSinceEpoch()
                except:
                    pass
            var_config.has_distribution = True
            var_config.has_min = True
            var_config.has_max = True
            var_config.min = var_input.min_input.dateTime().toSecsSinceEpoch()
            var_config.max = var_input.max_input.dateTime().toSecsSinceEpoch()
            var_config.dependencies = self.parse_dependencies(var_input,
                                                              var_type)
            var_config.values = self.parse_values(var_input, var_type)
            var_config.intervals = self.parse_intervals(var_input, var_type)
            var_config.used_information = var_input.info_used_input.currentIndex()
            rng = self.main.rng
            if var_input.distributions_input.currentIndex() == 0:
                distribution_type = "uniform"
            elif var_input.distributions_input.currentIndex() == 1:
                distribution_type = "normal"
            elif var_input.distributions_input.currentIndex() == 2:
                distribution_type = "exponential"
            other_arguments_dict = {"minimum": var_config.min,
                                    "maximum": var_config.max,
                                    "mean": var_input.distributions_mean_input.
                                    dateTime().toSecsSinceEpoch(),
                                    "standard_deviation": self.get_seconds_from_days_and_QTimeEdit(
                                        var_input.distributions_sd_input[0],
                                        var_input.distributions_sd_input[1])}

            var_config.has_sd = True
            var_config.has_avg = True
            var_config.sd = self.get_seconds_from_days_and_QTimeEdit(
                var_input.distributions_sd_input[0],
                var_input.distributions_sd_input[1])
            var_config.avg = var_input.distributions_mean_input.dateTime().toSecsSinceEpoch()

            distribution = Distribution(rng, distribution_type, other_arguments_dict)
            var_config.distribution = distribution
        elif var_type == VariableTypes.STRING:
            if var_config.use_initial_value and not var_config.generate_initial_value:
                var_config.initial_value = var_input.initial_input.text()
            else:
                try:
                    if var_input.initial_input.text() != "":
                        var_config.initial_value = var_input.initial_input.text()
                except:
                    pass
            var_config.has_distribution = False
            var_config.has_min = False
            var_config.has_max = False
            var_config.dependencies = self.parse_dependencies(var_input,
                                                              var_type)
            var_config.values = self.parse_values(var_input, var_type)
            variable.reset()

    def parse_dependencies(self, var_input: VariableInput, var_type: VariableTypes):
        dependencies = []
        text = var_input.dependencies_input.toPlainText()
        if text == "":
            return dependencies
        else:
            if "," in text:
                dependencies_str = text.split(",")
            else:
                dependencies_str = [text]
            for dependency_str in dependencies_str:
                parts = dependency_str.split("=>")
                logical_expression = parts[0].split('"')[1]
                constraint_str = parts[1].split('"')[1]
                constraint_operator = constraint_str.split(";")[0].split("'")[1].replace(" ", "")
                constraint_value = constraint_str.split(";")[1].split("'")[1]
                dependency = (logical_expression, (constraint_operator,
                                                   self.parse_variable_value(constraint_value,
                                                                             var_type,
                                                                             logical_expression,
                                                                             constraint_operator)))
                dependencies.append(dependency)
            return dependencies

    def parse_variable_value(self, value_str, var_type: VariableTypes, logical_expression,
                             constraint_operator):
        if logical_expression in ["SELF_REFERENCE", "self", "SELF", "self_reference",
                                  "Self_Reference"] and constraint_operator == "==":
            return value_str
        if var_type == VariableTypes.BOOL:
            if value_str in ["false", "False", "FALSE"]:
                return False
            else:
                return True
        elif var_type == VariableTypes.STRING:
            return value_str
        elif var_type == VariableTypes.INT or var_type == VariableTypes.LONG:
            return int(value_str)
        elif var_type == VariableTypes.DOUBLE:
            return float(value_str)
        elif var_type == VariableTypes.DATE:
            if logical_expression in ["SELF_REFERENCE", "self", "SELF",
                                      "self_reference", "Self_Reference"]:
                return self.get_seconds_from_string(value_str)
            else:
                return int(
                    QDateTime.fromString(value_str, "yyyy-MM-ddThh:mm:ss").toSecsSinceEpoch())

    def get_seconds_from_string(self, string):
        parts = string.split(":")
        return int(parts[0]) * 24 * 60 * 60 + int(parts[1]) * 60 * 60 + int(parts[2]) * 60 + \
               int(parts[3])

    def parse_values(self, var_input: VariableInput, var_type: VariableTypes):
        values = []
        weights = []
        text = var_input.values_input.toPlainText()
        if text == "":
            return [values, weights]
        else:
            if "|" in text:
                values_part = text.split("|")[0]
                weights_part = text.split("|")[1]
                if weights_part != "":
                    weights_str = weights_part.split(",")
                    for weight_str in weights_str:
                        weights.append(float(weight_str))
            else:
                values_part = text
            if "," in values_part:
                values_str = values_part.split(",")
            else:
                values_str = [values_part]
            for value_str in values_str:
                if '"' in value_str:
                    value = value_str.split('"')[1]
                    if var_type == VariableTypes.BOOL:
                        if value in ["false", "False", "FALSE"]:
                            values.append(False)
                        else:
                            values.append(True)
                    elif var_type == VariableTypes.STRING:
                        values.append(value)
                    elif var_type == VariableTypes.INT or var_type == VariableTypes.LONG:
                        values.append(int(value))
                    elif var_type == VariableTypes.DOUBLE:
                        values.append(float(value))
                    elif var_type == VariableTypes.DATE:
                        values.append(int(parse(value).timestamp()))
                else:
                    raise Exception()
            return [values, weights]

    def parse_intervals(self, var_input: VariableInput, var_type: VariableTypes):
        intervals = []
        text = var_input.intervals_input.toPlainText()
        if text == "":
            return intervals
        else:
            if "," in text:
                intervals_str = text.split(",")
            else:
                intervals_str = [text]
            for interval_str in intervals_str:
                interval = interval_str.split("(")[1].split(")")[0]
                operator = interval.split(";")[0].replace('"', "").replace(" ", "")
                value = interval.split(";")[1].split('"')[1]

                if var_type == VariableTypes.BOOL:
                    if value in ["false", "False", "FALSE"]:
                        intervals.append((operator, False))
                    else:
                        intervals.append((operator, True))
                elif var_type == VariableTypes.STRING:
                    intervals.append((operator, value))
                elif var_type == VariableTypes.INT or var_type == VariableTypes.LONG:
                    intervals.append((operator, int(value)))
                elif var_type == VariableTypes.DOUBLE:
                    intervals.append((operator, float(value)))
                elif var_type == VariableTypes.DATE:
                    intervals.append((operator,
                                      QDateTime.fromString(value, "yyyy-MM-ddThh:mm:ss")
                                      .toSecsSinceEpoch()))
            return intervals

    def configure_transitions_from_gui(self):
        config = self.main.config
        sim_config = config.simulation_config
        ui = self.window.ui

        sim_config.avg_timestamp_delay = self.get_seconds_from_days_and_QTimeEdit(
            ui.avg_trans_delay_days_input, ui.avg_trans_delay_time_input)

        sim_config.timestamp_delay_sd = self.get_seconds_from_days_and_QTimeEdit(
            ui.time_delay_sd_days_input, ui.time_delay_sd_time_input)

        sim_config.timestamp_delay_min = self.get_seconds_from_days_and_QTimeEdit(
            ui.time_delay_minimum_days_input, ui.time_delay_minimum_time_input)

        sim_config.timestamp_delay_max = self.get_seconds_from_days_and_QTimeEdit(
            ui.time_delay_maximum_days_input, ui.time_delay_maximum_time_input)

        sim_config.avg_timestamp_lead = self.get_seconds_from_days_and_QTimeEdit(
            ui.avg_trans_lead_days_input, ui.avg_trans_lead_time_input)

        sim_config.timestamp_lead_sd = self.get_seconds_from_days_and_QTimeEdit(
            ui.time_lead_sd_days_input, ui.time_lead_sd_time_input)

        sim_config.timestamp_lead_min = self.get_seconds_from_days_and_QTimeEdit(
            ui.time_lead_minimum_days_input, ui.time_lead_minimum_time_input)

        sim_config.timestamp_lead_max = self.get_seconds_from_days_and_QTimeEdit(
            ui.time_lead_maximum_days_input, ui.time_lead_maximum_time_input)

        for trans_input in self.transition_inputs:
            self.configure_transition(trans_input)

    def configure_transition(self, trans_input: TransitionInput):
        transition = trans_input.transition
        transition.invisible = trans_input.invisible_input.isChecked()

        trans_config = transition.config
        trans_config.invisible = trans_input.invisible_input.isChecked()
        trans_config.activity_name = trans_input.activity_name_input.text()
        trans_config.weight = trans_input.weight_input.value()
        trans_config.use_general_config = trans_input.general_config_input.isChecked()

        trans_config.avg_time_delay = self.get_seconds_from_days_and_QTimeEdit(
            trans_input.mean_delay_input[0], trans_input.mean_delay_input[1])

        trans_config.time_delay_sd = self.get_seconds_from_days_and_QTimeEdit(
            trans_input.delay_sd_input[0], trans_input.delay_sd_input[1])

        trans_config.time_delay_min = self.get_seconds_from_days_and_QTimeEdit(
            trans_input.delay_min_input[0], trans_input.delay_min_input[1])

        trans_config.time_delay_max = self.get_seconds_from_days_and_QTimeEdit(
            trans_input.delay_max_input[0], trans_input.delay_max_input[1])

        trans_config.avg_lead_time = self.get_seconds_from_days_and_QTimeEdit(
            trans_input.lead_mean_input[0], trans_input.lead_mean_input[1])

        trans_config.lead_time_sd = self.get_seconds_from_days_and_QTimeEdit(
            trans_input.lead_sd_input[0], trans_input.lead_sd_input[1])

        trans_config.lead_time_min = self.get_seconds_from_days_and_QTimeEdit(
            trans_input.lead_min_input[0], trans_input.lead_min_input[1])

        trans_config.lead_time_max = self.get_seconds_from_days_and_QTimeEdit(
            trans_input.lead_max_input[0], trans_input.lead_max_input[1])

        trans_config.no_time_forward = trans_input.no_time_forwarding_input.isChecked()

        trans_config.included_vars = []
        for input in trans_input.included_vars:
            if input[1].isChecked():
                trans_config.included_vars.append(input[0])

        trans_config.add_time_interval_variance = trans_input.variance_input.isChecked()
        trans_config.max_time_interval_variance = trans_input.max_variance_input.value()
        trans_config.time_intervals = self.parse_time_intervals(trans_input.time_intervals_input)

    def parse_time_intervals(self, time_intervals_input):
        input_text = time_intervals_input.toPlainText().replace(" ", "").replace("\n", "")
        if input_text == "":
            return []
        if ";" in input_text:
            return input_text.split(";")
        else:
            return [input_text]

    def get_variable_checkbox_by_name(self, name, inputs):
        for input in inputs:
            if input[0] == name:
                return input[1]

    def get_seconds_from_days_and_QTimeEdit(self, days_input, time_input):
        time = time_input.time()
        return (days_input.value() * 24 * 60 * 60) + ((time.hour() * 60 * 60) + (time.minute() * 60)
                                                      + (time.second()))

    def configure_combo_boxes(self):
        self.window.ui.sim_strategy_input.addItems(["Random Trace Generation", "Random Exploration",
                                                    "All Traces (Experimental)"])
        self.window.ui.sim_strategy_input.currentIndexChanged. \
            connect(self.change_simulation_config_gui)

    def configure_scroll_areas(self):
        self.variable_layout = QVBoxLayout()
        self.variable_layout.setSpacing(25)
        self.transition_layout = QVBoxLayout()
        self.transition_layout.setSpacing(25)
        self.sim_config_layout = QVBoxLayout()
        self.sim_config_layout.setSpacing(10)
        ui = self.window.ui
        ui.scrollAreaWidgetContents.setLayout(self.transition_layout)

        self.transition_layout.addWidget(ui.general_config_2)

        ui.scrollAreaWidgetContents_3.setLayout(self.variable_layout)
        ui.scrollAreaWidgetContents_7.setLayout(self.sim_config_layout)
        ui.general_config_2.setFixedHeight(651)
        ui.general_config_3.setFixedHeight(71)

        widgets = [ui.sim_strategy,
                   ui.trace_estimation,
                   ui.trace_name,
                   ui.nr_of_traces,
                   ui.max_trace_length,
                   ui.min_trace_length,
                   ui.max_loop_iterations,
                   ui.max_loop_iterations_transition,
                   ui.max_trace_duplicates,
                   ui.duplicates_with_data,
                   ui.duplicates_with_invisible_trans,
                   ui.only_ending_traces,
                   ui.include_partial_traces,
                   ui.merge_intervals,
                   ui.limit_variable_values,
                   ui.timestamp_anchor,
                   ui.utc_offset,
                   ui.fixed_timestamp_anchor,
                   ui.seed]

        for widget in widgets:
            widget.setFixedHeight(widget.height() + 5)
            self.sim_config_layout.addWidget(widget)

    def add_variable_input_widget(self, variable):
        ui_file_path = os.getcwd() + "/src/resources/QtDesignerFiles/"
        if variable.type == VariableTypes.STRING:
            ui_file_path += "VariableInputString.ui"
        elif variable.type == VariableTypes.DATE:
            ui_file_path += "VariableInputDate.ui"
        elif variable.type == VariableTypes.BOOL:
            ui_file_path += "VariableInputBool.ui"
        elif variable.type == VariableTypes.DOUBLE:
            ui_file_path += "VariableInputDouble.ui"
        else:
            ui_file_path += "VariableInputInt.ui"
        ui_file = QFile(ui_file_path)
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        widget = loader.load(ui_file, self.window.ui.scrollAreaWidgetContents_3)
        # widget.setObjectName("variable_input"+str(len(self.variable_inputs)))
        widget.setFixedHeight(widget.height())
        widget.setFixedWidth(widget.width())
        widget.findChild(QLabel, name="header_label").setText(variable.original_name + " (" +
                                                              str(variable.type.value.split(".")
                                                                  [-1]) + ")")
        self.variable_layout.addWidget(widget)

        values_input = widget.findChild(QPlainTextEdit, name="values_input")
        dependencies_input = widget.findChild(QPlainTextEdit, name="dependencies_input")
        dependencies_input.setPlainText(variable.semantic_information.get_dependencies_string(
            variable.type))
        values_input.setPlainText(variable.semantic_information.get_values_string(self.main.model))

        initial_input, min_input, max_input, distributions_input, initial_input2, \
        info_used_input, distributions_mean_input, distributions_sd_input, intervals_input, \
        use_initial_value_input, inverse_intervals_input, precision_input, gen_initial_value_input, \
        fixed_variable_input, trace_variable_input, self_deviation_input, self_deviation_input2 = \
            (None, None, None, None, None, None, None, None, None, None, None, None, None, None,
             None, None, None)
        gen_initial_value_input = widget.findChild(QCheckBox, name="gen_initial_value_input")
        use_initial_value_input = widget.findChild(QCheckBox, name="use_initial_value_input")

        fixed_variable_input = widget.findChild(QCheckBox, name="fixed_variable_input")
        trace_variable_input = widget.findChild(QCheckBox, name="trace_variable_input")

        if variable.type == VariableTypes.BOOL:
            values_input.setPlainText('"True", "False" | 1, 1')

            initial_input = widget.findChild(QRadioButton, name="initial_value_input_true")
            initial_input2 = widget.findChild(QRadioButton, name="initial_value_input_false")

        elif variable.type == VariableTypes.INT or variable.type == VariableTypes.LONG:

            self_deviation_input = widget.findChild(QSpinBox, name="self_deviation_input")

            inverse_intervals_input = widget.findChild(QCheckBox, name="inverse_intervals_input")
            initial_input = widget.findChild(QSpinBox, name="initial_value_input")
            min_input = widget.findChild(QSpinBox, name="minimum_value_input")
            max_input = widget.findChild(QSpinBox, name="maximum_value_input")
            info_used_input = widget.findChild(QComboBox, name="used_info_input")
            distributions_input = widget.findChild(QComboBox, name="distribution_input")
            distributions_mean_input = widget.findChild(QDoubleSpinBox,
                                                        name="distribution_mean_input")
            distributions_sd_input = widget.findChild(QDoubleSpinBox, name="distribution_sd_input")
            intervals_input = widget.findChild(QPlainTextEdit, name="intervals_input")
            intervals_input.setPlainText(variable.semantic_information.get_intervals_string(
                self.main.model))

            info_used_input.addItems(["Values", "Intervals", "Distribution"])
            info_used_input.setCurrentIndex(0)

            distributions_input.addItems(["Uniform", "Normal", "Exponential"])
            distributions_input.currentIndexChanged.connect(
                lambda: self.change_variable_input_widget_distribution(
                    var_input, distributions_input))
            info_used_input.setCurrentIndex(0)

        elif variable.type == VariableTypes.DOUBLE:
            self_deviation_input = widget.findChild(QDoubleSpinBox, name="self_deviation_input")
            precision_input = widget.findChild(QSpinBox, name="precision_input")
            precision_input.valueChanged.connect(
                lambda: self.change_decimal_input(var_input))
            inverse_intervals_input = widget.findChild(QCheckBox, name="inverse_intervals_input")
            initial_input = widget.findChild(QDoubleSpinBox, name="initial_value_input")
            min_input = widget.findChild(QDoubleSpinBox, name="minimum_value_input")
            max_input = widget.findChild(QDoubleSpinBox, name="maximum_value_input")
            info_used_input = widget.findChild(QComboBox, name="used_info_input")
            distributions_input = widget.findChild(QComboBox, name="distribution_input")
            distributions_mean_input = widget.findChild(QDoubleSpinBox,
                                                        name="distribution_mean_input")
            distributions_sd_input = widget.findChild(QDoubleSpinBox, name="distribution_sd_input")
            intervals_input = widget.findChild(QPlainTextEdit, name="intervals_input")
            intervals_input.setPlainText(variable.semantic_information.get_intervals_string(
                self.main.model))

            info_used_input.addItems(["Values", "Intervals", "Distribution"])
            info_used_input.setCurrentIndex(0)

            distributions_input.addItems(["Uniform", "Normal", "Exponential"])
            distributions_input.currentIndexChanged.connect(
                lambda: self.change_variable_input_widget_distribution(
                    var_input, distributions_input))
            info_used_input.setCurrentIndex(0)

        elif variable.type == VariableTypes.STRING:

            initial_input = widget.findChild(QLineEdit, name="initial_value_input")
        elif variable.type == VariableTypes.DATE:
            self_deviation_input = widget.findChild(QSpinBox, name="self_deviation_input_days")
            self_deviation_input2 = widget.findChild(QTimeEdit, name="self_deviation_input_time")

            inverse_intervals_input = widget.findChild(QCheckBox, name="inverse_intervals_input")
            initial_input = widget.findChild(QDateTimeEdit, name="initial_value_input")
            min_input = widget.findChild(QDateTimeEdit, name="minimum_value_input")
            max_input = widget.findChild(QDateTimeEdit, name="maximum_value_input")
            info_used_input = widget.findChild(QComboBox, name="used_info_input")
            distributions_input = widget.findChild(QComboBox, name="distribution_input")
            distributions_mean_input = widget.findChild(QDateTimeEdit,
                                                        name="distribution_mean_input")
            distributions_sd_input = [widget.findChild(QSpinBox,
                                                       name="distribution_sd_input_days"),
                                      widget.findChild(QTimeEdit,
                                                       name="distribution_sd_input_time"),
                                      ]
            intervals_input = widget.findChild(QPlainTextEdit, name="intervals_input")
            intervals_input.setPlainText(variable.semantic_information.get_intervals_string(
                self.main.model))

            info_used_input.addItems(["Values", "Intervals", "Distribution"])
            info_used_input.setCurrentIndex(0)

            distributions_input.addItems(["Uniform", "Normal", "Exponential"])
            distributions_input.currentIndexChanged.connect(
                lambda: self.change_variable_input_widget_distribution(
                    var_input, distributions_input))
            info_used_input.setCurrentIndex(0)
        else:
            print("THIS SHOULD NOT BE REACHED!")

        var_input = VariableInput(variable, initial_input, min_input, max_input, values_input,
                                  dependencies_input, distributions_input, initial_input2,
                                  info_used_input, distributions_mean_input, distributions_sd_input,
                                  intervals_input, use_initial_value_input, widget,
                                  inverse_intervals_input, precision_input, gen_initial_value_input,
                                  fixed_variable_input, trace_variable_input, self_deviation_input,
                                  self_deviation_input2)
        var_input.use_initial_value_input.stateChanged.connect(
            lambda: self.change_variable_input_widget_initial_value(var_input))
        var_input.gen_initial_value_input.stateChanged.connect(
            lambda: self.change_variable_input_widget_initial_value_generated(var_input))

        self.change_variable_input_widget_initial_value(var_input)
        if var_input.variable.type == VariableTypes.INT or \
                var_input.variable.type == VariableTypes.LONG or \
                var_input.variable.type == VariableTypes.DOUBLE or \
                var_input.variable.type == VariableTypes.DATE:
            var_input.info_used_input.currentIndexChanged.connect(
                lambda: self.change_variable_input_widget(var_input))
            self.change_variable_input_widget(var_input)
        if variable.type in [VariableTypes.INT, VariableTypes.LONG, VariableTypes.DATE,
                             VariableTypes.DOUBLE]:
            if len(variable.semantic_information.intervals) > 1:
                var_input.info_used_input.setCurrentIndex(1)
                self.change_variable_input_widget(var_input)
            else:
                var_input.info_used_input.setCurrentIndex(2)
                self.change_variable_input_widget(var_input)
        self.variable_inputs.append(var_input)

    def change_variable_input_widget_distribution(self, var_input, distributions_input):
        if var_input.variable.type == VariableTypes.DATE:
            if distributions_input.currentIndex() == 0:
                var_input.distributions_sd_input[0].setEnabled(False)
                var_input.distributions_sd_input[1].setEnabled(False)
                var_input.distributions_mean_input.setEnabled(False)
            elif distributions_input.currentIndex() == 1:
                var_input.distributions_sd_input[0].setEnabled(True)
                var_input.distributions_sd_input[1].setEnabled(True)
                var_input.distributions_mean_input.setEnabled(True)
            else:
                var_input.distributions_sd_input[0].setEnabled(True)
                var_input.distributions_sd_input[1].setEnabled(True)
                var_input.distributions_mean_input.setEnabled(False)
        else:
            if distributions_input.currentIndex() == 0:
                var_input.distributions_sd_input.setEnabled(False)
                var_input.distributions_mean_input.setEnabled(False)
            elif distributions_input.currentIndex() == 1:
                var_input.distributions_sd_input.setEnabled(True)
                var_input.distributions_mean_input.setEnabled(True)
            else:
                var_input.distributions_sd_input.setEnabled(True)
                var_input.distributions_mean_input.setEnabled(False)

    def change_variable_input_widget(self, var_input):
        index = var_input.info_used_input.currentIndex()
        if index == 0:  # "Values and Dependencies"
            var_input.values_input.setEnabled(True)
            var_input.intervals_input.setEnabled(False)
            var_input.inverse_intervals_input.setEnabled(False)
            var_input.distributions_input.setEnabled(False)
            var_input.inverse_intervals_input.setEnabled(False)
            if var_input.variable.type == VariableTypes.DATE:
                var_input.distributions_sd_input[0].setEnabled(False)
                var_input.distributions_sd_input[1].setEnabled(False)
            else:
                var_input.distributions_sd_input.setEnabled(False)
            var_input.distributions_mean_input.setEnabled(False)
            var_input.min_input.setEnabled(True)
            var_input.max_input.setEnabled(True)
        elif index == 1:  # "Intervals"
            var_input.inverse_intervals_input.setEnabled(True)
            var_input.values_input.setEnabled(False)
            var_input.intervals_input.setEnabled(True)
            var_input.inverse_intervals_input.setEnabled(True)
            var_input.distributions_input.setEnabled(False)
            if var_input.variable.type == VariableTypes.DATE:
                var_input.distributions_sd_input[0].setEnabled(False)
                var_input.distributions_sd_input[1].setEnabled(False)
            else:
                var_input.distributions_sd_input.setEnabled(False)
            var_input.distributions_mean_input.setEnabled(False)
            var_input.min_input.setEnabled(True)
            var_input.max_input.setEnabled(True)
        else:  # "Distribution"
            var_input.values_input.setEnabled(False)
            var_input.intervals_input.setEnabled(False)
            var_input.inverse_intervals_input.setEnabled(False)
            var_input.distributions_input.setEnabled(True)
            if var_input.variable.type == VariableTypes.DATE:
                var_input.distributions_sd_input[0].setEnabled(True)
                var_input.distributions_sd_input[1].setEnabled(True)
            else:
                var_input.distributions_sd_input.setEnabled(True)
            var_input.distributions_mean_input.setEnabled(True)
            var_input.min_input.setEnabled(True)
            var_input.max_input.setEnabled(True)
            self.change_variable_input_widget_distribution(var_input, var_input.distributions_input)

    def change_variable_input_widget_initial_value_generated(self, var_input):
        if var_input.gen_initial_value_input.isChecked():
            var_input.initial_input.setEnabled(False)
            if var_input.initial_input2 is not None:
                var_input.initial_input2.setEnabled(False)
        else:
            var_input.initial_input.setEnabled(True)
            if var_input.initial_input2 is not None:
                var_input.initial_input2.setEnabled(True)

    def change_variable_input_widget_initial_value(self, var_input):
        is_checked = var_input.use_initial_value_input.isChecked()
        if is_checked:
            var_input.gen_initial_value_input.setEnabled(True)
            if var_input.gen_initial_value_input.isChecked():
                var_input.initial_input.setEnabled(False)
            else:
                var_input.initial_input.setEnabled(True)
            if var_input.initial_input2 is not None:
                var_input.initial_input2.setEnabled(True)
        else:
            var_input.gen_initial_value_input.setChecked(False)
            var_input.initial_input.setEnabled(False)
            var_input.gen_initial_value_input.setEnabled(False)
            if var_input.initial_input2 is not None:
                var_input.initial_input2.setEnabled(False)

    def add_transition_input_widget(self, transition):
        ui_file_path = os.getcwd() + "/src/resources/QtDesignerFiles/TransitionsInput.ui"

        ui_file = QFile(ui_file_path)
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        widget = loader.load(ui_file, self.window.ui.scrollAreaWidgetContents)
        widget.setFixedHeight(widget.height())
        widget.setFixedWidth(widget.width())
        widget.findChild(QLabel, name="header_label").setText(transition.name + " (" +
                                                              transition.id + ")")
        self.transition_layout.addWidget(widget)

        activity_name_input = widget.findChild(QLineEdit, name="activity_name_input")
        weight_input = widget.findChild(QDoubleSpinBox, name="weight_input")
        invisible_input = widget.findChild(QCheckBox, name="invisible_input")

        mean_delay_input = [widget.findChild(QSpinBox, name="avg_trans_delay_days_input"),
                            widget.findChild(QTimeEdit, name="avg_trans_delay_time_input")]

        delay_sd_input = [widget.findChild(QSpinBox, name="time_delay_sd_days_input"),
                          widget.findChild(QTimeEdit, name="time_delay_sd_time_input")]

        delay_min_input = [widget.findChild(QSpinBox, name="time_delay_minimum_days_input"),
                           widget.findChild(QTimeEdit, name="time_delay_minimum_time_input")]
        delay_min_input[1].setTime(QTime(0, 0, 0))

        delay_max_input = [widget.findChild(QSpinBox, name="time_delay_maximum_days_input"),
                           widget.findChild(QTimeEdit, name="time_delay_maximum_time_input")]

        lead_mean_input = [widget.findChild(QSpinBox, name="avg_trans_lead_days_input"),
                           widget.findChild(QTimeEdit, name="avg_trans_lead_time_input")]

        lead_sd_input = [widget.findChild(QSpinBox, name="time_lead_sd_days_input"),
                         widget.findChild(QTimeEdit, name="time_lead_sd_time_input")]

        lead_min_input = [widget.findChild(QSpinBox, name="time_lead_minimum_days_input"),
                          widget.findChild(QTimeEdit, name="time_lead_minimum_time_input")]
        lead_min_input[1].setTime(QTime(0, 0, 0))

        lead_max_input = [widget.findChild(QSpinBox, name="time_lead_maximum_days_input"),
                          widget.findChild(QTimeEdit, name="time_lead_maximum_time_input")]

        general_config_input = widget.findChild(QCheckBox, name="general_config_input")

        scroll_area = widget.findChild(QWidget, name="scroll_area_contents")

        no_time_forwarding_input = widget.findChild(QCheckBox, name="no_time_forwarding_input")
        variance_input = widget.findChild(QCheckBox, name="variance_input")
        max_variance_input = widget.findChild(QSpinBox, name="max_variance_input")
        time_intervals_input = widget.findChild(QPlainTextEdit, name="time_intervals_input")

        layout = QVBoxLayout()
        layout.setSpacing(3)
        scroll_area.setLayout(layout)
        included_vars = []
        # ui_file_path = os.getcwd() + "/src/resources/QtDesignerFiles/IncludedVariablesInput.ui"
        for variable in self.main.model.variables:
            # ui_file = QFile(ui_file_path)
            # ui_file.open(QFile.ReadOnly)
            # loader = QUiLoader()
            # var_widget = loader.load(ui_file, scroll_area)
            # var_widget.setFixedHeight(var_widget.height())
            # var_widget.setFixedWidth(var_widget.width())
            # label = var_widget.findChild(QLabel, name="name_label")
            # check_box = var_widget.findChild(QCheckBox, name="check_box_input")

            var_widget = QWidget(scroll_area)
            var_widget.setFixedHeight(24)
            var_widget.setFixedWidth(243)
            label = QLabel(var_widget)
            label.setStyleSheet("font-size: 12pt")
            label.setFixedWidth(141)
            label.setFixedHeight(21)
            label.move(10, 0)
            check_box = QCheckBox(var_widget)
            check_box.move(200, 0)

            check_box.setChecked(True)
            included_vars.append((variable.original_name, check_box))
            label.setText(variable.original_name + ":")
            layout.addWidget(var_widget)

        trans_input = TransitionInput(transition, activity_name_input, weight_input,
                                      invisible_input, mean_delay_input, delay_sd_input,
                                      delay_min_input, delay_max_input, lead_mean_input,
                                      lead_min_input, lead_max_input, lead_sd_input,
                                      general_config_input, widget, scroll_area, included_vars,
                                      no_time_forwarding_input, variance_input, max_variance_input,
                                      time_intervals_input)
        weight_input.setValue(1)
        activity_name_input.setText(transition.name)
        trans_input.general_config_input.stateChanged.connect(
            lambda: self.change_transition_input_widget(trans_input))

        trans_input.variance_input.stateChanged.connect(
            lambda: self.change_transition_input_widget(trans_input))

        trans_input.no_time_forwarding_input.stateChanged.connect(
            lambda: self.change_transition_input_widget(trans_input))
        if transition.invisible:
            invisible_input.setChecked(True)
        else:
            invisible_input.setChecked(False)
        trans_input.general_config_input.setChecked(False)
        trans_input.general_config_input.setChecked(True)

        self.transition_inputs.append(trans_input)

    def change_transition_input_widget(self, trans_input):
        if trans_input.general_config_input.isChecked():
            trans_input.mean_delay_input[0].setEnabled(False)
            trans_input.mean_delay_input[1].setEnabled(False)
            trans_input.delay_sd_input[0].setEnabled(False)
            trans_input.delay_sd_input[1].setEnabled(False)
            trans_input.delay_min_input[0].setEnabled(False)
            trans_input.delay_min_input[1].setEnabled(False)
            trans_input.delay_max_input[0].setEnabled(False)
            trans_input.delay_max_input[1].setEnabled(False)
            trans_input.lead_min_input[0].setEnabled(False)
            trans_input.lead_min_input[1].setEnabled(False)
            trans_input.lead_max_input[0].setEnabled(False)
            trans_input.lead_max_input[1].setEnabled(False)
            trans_input.lead_mean_input[0].setEnabled(False)
            trans_input.lead_mean_input[1].setEnabled(False)
            trans_input.lead_sd_input[0].setEnabled(False)
            trans_input.lead_sd_input[1].setEnabled(False)
            trans_input.no_time_forwarding_input.setEnabled(False)
            trans_input.time_intervals_input.setEnabled(False)
            trans_input.variance_input.setEnabled(False)
            trans_input.max_variance_input.setEnabled(False)
        elif trans_input.no_time_forwarding_input.isChecked():
            trans_input.mean_delay_input[0].setEnabled(False)
            trans_input.mean_delay_input[1].setEnabled(False)
            trans_input.delay_sd_input[0].setEnabled(False)
            trans_input.delay_sd_input[1].setEnabled(False)
            trans_input.delay_min_input[0].setEnabled(False)
            trans_input.delay_min_input[1].setEnabled(False)
            trans_input.delay_max_input[0].setEnabled(False)
            trans_input.delay_max_input[1].setEnabled(False)
            trans_input.lead_min_input[0].setEnabled(False)
            trans_input.lead_min_input[1].setEnabled(False)
            trans_input.lead_max_input[0].setEnabled(False)
            trans_input.lead_max_input[1].setEnabled(False)
            trans_input.lead_mean_input[0].setEnabled(False)
            trans_input.lead_mean_input[1].setEnabled(False)
            trans_input.lead_sd_input[0].setEnabled(False)
            trans_input.lead_sd_input[1].setEnabled(False)
            trans_input.no_time_forwarding_input.setEnabled(True)
            trans_input.time_intervals_input.setEnabled(True)
            trans_input.variance_input.setEnabled(False)
            trans_input.max_variance_input.setEnabled(False)
        else:
            trans_input.mean_delay_input[0].setEnabled(True)
            trans_input.mean_delay_input[1].setEnabled(True)
            trans_input.delay_sd_input[0].setEnabled(True)
            trans_input.delay_sd_input[1].setEnabled(True)
            trans_input.delay_min_input[0].setEnabled(True)
            trans_input.delay_min_input[1].setEnabled(True)
            trans_input.delay_max_input[0].setEnabled(True)
            trans_input.delay_max_input[1].setEnabled(True)
            trans_input.lead_min_input[0].setEnabled(True)
            trans_input.lead_min_input[1].setEnabled(True)
            trans_input.lead_max_input[0].setEnabled(True)
            trans_input.lead_max_input[1].setEnabled(True)
            trans_input.lead_mean_input[0].setEnabled(True)
            trans_input.lead_mean_input[1].setEnabled(True)
            trans_input.lead_sd_input[0].setEnabled(True)
            trans_input.lead_sd_input[1].setEnabled(True)
            trans_input.no_time_forwarding_input.setEnabled(True)
            trans_input.time_intervals_input.setEnabled(True)
            trans_input.variance_input.setEnabled(True)
            if trans_input.variance_input.isChecked():
                trans_input.max_variance_input.setEnabled(True)
            else:
                trans_input.max_variance_input.setEnabled(False)

    def set_output_dir(self):
        my_dir = QFileDialog.getExistingDirectory(self.window, "Open a folder", os.getcwd())
        if my_dir:
            self.window.ui.output_path_input.setText(my_dir)

    def process_model_has_no_changing_loop_signal(self):
        if self.window.ui.changing_loop_input.isChecked():
            if self.window.ui.sim_strategy_input.currentIndex() == 1 or \
                    self.window.ui.sim_strategy_input.currentIndex() == 2:
                self.window.ui.max_loop_iterations.setHidden(False)
        else:
            if self.window.ui.sim_strategy_input.currentIndex() == 1 or \
                    self.window.ui.sim_strategy_input.currentIndex() == 2:
                self.window.ui.max_loop_iterations.setHidden(True)

    def process_only_ending_traces_signal(self):
        if self.window.ui.only_ending_traces_input.isChecked():
            self.window.ui.include_partial_traces.setEnabled(False)
            self.window.ui.partial_traces_input.setChecked(False)
        else:
            self.window.ui.include_partial_traces.setEnabled(True)

    def update_gui_and_config(self):
        config = self.main.config
        ui = self.window.ui
        if ui.file_name_input.text() == "":
            ui.file_name_input.setText(config.event_log_name)
        else:
            config.event_log_name = ui.file_name_input.text()

        config.number_of_event_logs = ui.nr_of_event_logs_input.value()

        if ui.output_path_input.text() == "":
            ui.output_path_input.setText(config.output_directory_path)
        else:
            config.output_directory_path = ui.output_path_input.text()

        if ui.sim_strategy_input.currentIndex() == 0:
            config.simulation_config.sim_strategy = "random"
        elif ui.sim_strategy_input.currentIndex() == 1:
            config.simulation_config.sim_strategy = "random_exploration"
        else:
            config.simulation_config.sim_strategy = "all"
        ui.seed_input.setText(str(self.main.config.simulation_config.random_seed))
        self.update_config_from_gui()

    def get_days_hours_min_sec(self, timestamp):
        days = timestamp // (24 * 3600)
        timestamp = timestamp % (24 * 3600)
        hours = timestamp // 3600
        timestamp %= 3600
        minutes = timestamp // 60
        timestamp %= 60
        seconds = timestamp
        return days, hours, minutes, seconds

    def load_config(self):
        file_path = QFileDialog.getOpenFileName(self.window, 'Load configuration', os.getcwd(),
                                                "JSON File (*.json)")[0]
        try:
            if file_path:
                if self.status == Status.SIM_RUNNING:
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    msg.setText("Can not load file while the simulation is running!")
                    msg.setWindowTitle("Error")
                    msg.exec()
                elif self.status == Status.MODEL_LOADED:
                    model_fits, model_path = self.check_if_config_fits_model(file_path,
                                                                             self.main.model)
                    if model_fits:
                        self.main.config.read_config_file(file_path, self.main.model)
                        self.update_gui_from_config()
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.NoIcon)
                        msg.setText("Configuration file loaded successfully!")
                        msg.setWindowTitle("Success!")
                        msg.setButtonText(1, "Ok")
                        msg.exec()
                    else:
                        if os.path.isfile(model_path):
                            ret = QMessageBox.question(self.window, '',
                                                       "It looks like the specified configuration file was"
                                                       " saved when a different model was loaded. The model"
                                                       " that was loaded at the time"
                                                       " at which the configuration file was written needs"
                                                       " to be present in order to load the configuration"
                                                       " file. The model path saved in the configuration"
                                                       " file is is: \n\n'{path}' \n\n"
                                                       " Should"
                                                       " the program try to load the missing model?".format(
                                                           path=model_path
                                                       ),
                                                       QMessageBox.Yes | QMessageBox.No)
                            if ret == QMessageBox.Yes:
                                success = self.load_pnml(model_path)
                                if success:
                                    self.main.config.read_config_file(file_path, self.main.model)
                                    self.update_gui_from_config()
                                    msg = QMessageBox()
                                    msg.setIcon(QMessageBox.NoIcon)
                                    msg.setText("Model and Configuration file loaded successfully!")
                                    msg.setWindowTitle("Success!")
                                    msg.setButtonText(1, "Ok")
                                    msg.exec()
                            else:
                                msg = QMessageBox()
                                msg.setIcon(QMessageBox.NoIcon)
                                msg.setText("No Configuration file was loaded.")
                                msg.setWindowTitle("Information")
                                msg.setButtonText(1, "Ok")
                                msg.exec()
                        else:
                            msg = QMessageBox()
                            msg.setIcon(QMessageBox.NoIcon)
                            msg.setText("It looks like the specified configuration file was"
                                        " saved when a model was loaded. The model"
                                        " that was loaded at the time"
                                        " at which the configuration file was written needs"
                                        " to be present in order to load the "
                                        "configuration"
                                        " file. The model path saved in the configuration"
                                        " file is: \n\n'{path}' \n\n"
                                        "However the model from the above path could not be found!"
                                        " You can solve this problem by first loaded the needed"
                                        " model"
                                        " and then loading the configuration file"
                                        "".format(path=model_path))
                            msg.setWindowTitle("Information")
                            msg.setButtonText(1, "Ok")
                            msg.exec()
                else:
                    model_needed, model_path = self.check_if_model_is_needed_for_config(file_path)
                    if model_needed:
                        if os.path.isfile(model_path):
                            ret = QMessageBox.question(self.window, '',
                                                       "It looks like the specified configuration file was"
                                                       " saved when a model was loaded that is currently"
                                                       " not provided. The model"
                                                       " that was loaded at the time"
                                                       " at which the configuration file was written needs"
                                                       " to be present in order to load the configuration"
                                                       " file. The model path saved in the configuration"
                                                       " file is is: \n\n'{path}' \n\n"
                                                       " Should"
                                                       " the program try to load the missing model?".format(
                                                           path=model_path
                                                       ),
                                                       QMessageBox.Yes | QMessageBox.No)

                            if ret == QMessageBox.Yes:
                                success = self.load_pnml(model_path)
                                if success:
                                    self.main.config.read_config_file(file_path, self.main.model)
                                    self.update_gui_from_config()
                                    msg = QMessageBox()
                                    msg.setIcon(QMessageBox.NoIcon)
                                    msg.setText("Model and Configuration file loaded successfully!")
                                    msg.setWindowTitle("Success!")
                                    msg.setButtonText(1, "Ok")
                                    msg.exec()
                            else:
                                msg = QMessageBox()
                                msg.setIcon(QMessageBox.NoIcon)
                                msg.setText("No Configuration file was loaded.")
                                msg.setWindowTitle("Information")
                                msg.setButtonText(1, "Ok")
                                msg.exec()
                        else:
                            msg = QMessageBox()
                            msg.setIcon(QMessageBox.NoIcon)
                            msg.setText("It looks like the specified configuration file was"
                                        " saved when a model was loaded. The model"
                                        " that was loaded at the time"
                                        " at which the configuration file was written needs"
                                        " to be present in order to load the "
                                        "configuration"
                                        " file. The model path saved in the configuration"
                                        " file is: \n\n'{path}' \n\n"
                                        "However the model from the above path could not be found!"
                                        " You can solve this problem by first loaded the needed"
                                        " model"
                                        " and then loading the configuration file"
                                        "".format(path=model_path))
                            msg.setWindowTitle("Information")
                            msg.setButtonText(1, "Ok")
                            msg.exec()
                    else:
                        self.main.config = Configuration(None)
                        self.main.config.read_config_file(file_path, None, False)
                        self.update_gui_from_config()
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.NoIcon)
                        msg.setText("Configuration file loaded successfully!")
                        msg.setWindowTitle("Success!")
                        msg.setButtonText(1, "Ok")
                        msg.exec()
        except:
            self.display_error_msg(str(traceback.format_exc()),
                                   "An Error occurred while loading the configuration file!")

    def display_error_msg(self, traceback, text):
        if text is None:
            text = "An Error occurred!"
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(text)
        msg.setWindowTitle("Error!")
        msg.setInformativeText(traceback)
        msg.setButtonText(1, "Ok")
        msg.exec()

    def check_if_model_is_needed_for_config(self, file_path):
        with open(file_path) as config_file:
            json_data = json.load(config_file)
        if json_data["semantic_information"]:
            return True, json_data["model_file_path"]
        elif json_data["simulation_config"]["transition_configs"]:
            return True, json_data["model_file_path"]
        else:
            return False, ""

    def check_if_config_fits_model(self, file_path, model):
        with open(file_path) as config_file:
            json_data = json.load(config_file)
        model_path = json_data["model_file_path"]
        sem_infos = json_data["semantic_information"]
        trans_configs = json_data["simulation_config"]["transition_configs"]
        for variable in model.variables:
            var_config_found = False
            for sem_info in sem_infos:
                try:
                    var_name = sem_info["variable_name"]
                    if var_name == variable.original_name:
                        var_config_found = True
                except KeyError:
                    return False, model_path
            if not var_config_found:
                return False, model_path

        for transition in model.transitions:
            trans_config_found = False
            for trans_config in trans_configs:
                try:
                    trans_id = trans_config["transition_id"]
                    if trans_id == transition.id:
                        trans_config_found = True
                except KeyError:
                    return False, model_path
            if not trans_config_found:
                return False, model_path
        return True, ""

    def update_gui_from_config(self):
        ui = self.window.ui
        config = self.main.config
        sim_config = config.simulation_config
        ui.output_path_input.setText(config.output_directory_path)
        ui.nr_of_event_logs_input.setValue(config.number_of_event_logs)
        ui.file_name_input.setText(config.event_log_name)
        ui.include_config_input.setChecked(config.copy_config_to_output_dir)

        ui.include_metadata_input.setChecked(config.include_metadata)

        if sim_config.sim_strategy == "random":
            ui.sim_strategy_input.setCurrentIndex(0)
        elif sim_config.sim_strategy == "random_exploration":
            ui.sim_strategy_input.setCurrentIndex(1)
        else:
            ui.sim_strategy_input.setCurrentIndex(2)

        ui.inlcude_values_in_origin_event_input.setChecked(sim_config.values_in_origin_event)

        ui.nr_of_traces_input.setValue(sim_config.number_of_traces)
        ui.max_trace_length_input.setValue(sim_config.max_trace_length)
        ui.min_trace_length_input.setValue(sim_config.min_trace_length)
        ui.max_loop_iterations_input.setValue(sim_config.max_loop_iterations)
        ui.max_loop_iterations_transitions_input.setValue(
            sim_config.max_loop_iterations_transitions)
        ui.max_trace_duplicates_input.setValue(sim_config.max_trace_duplicates)
        ui.duplicates_with_data_input.setChecked(sim_config.duplicates_with_data_perspective)
        ui.only_ending_traces_input.setChecked(sim_config.only_ending_traces)
        ui.partial_traces_input.setChecked(sim_config.include_partial_traces)

        ui.merge_intervals_input.setChecked(sim_config.merge_intervals)
        ui.limit_variable_values_input.setChecked(sim_config.use_only_values_from_guard_strings)

        tmp = QDateTime.fromSecsSinceEpoch(int(sim_config.timestamp_anchor.timestamp()))
        ui.timestamp_anchor_input.setDateTime(tmp)

        ui.fixed_timestamp_anchor_input.setChecked(sim_config.fixed_timestamp)
        ui.seed_input.setText(str(sim_config.random_seed))
        ui.changing_loop_input.setChecked(sim_config.model_has_no_increasing_loop)

        ui.trace_name_input.setText(sim_config.trace_names[0])
        ui.utc_offset_input.setValue(sim_config.utc_offset)

        ui.trace_estimation_input.setChecked(sim_config.perform_trace_estimation)

        days, qtime = self.get_days_and_qtime_from_seconds(sim_config.avg_timestamp_delay)
        ui.avg_trans_delay_time_input.setTime(qtime)
        ui.avg_trans_delay_days_input.setValue(days)

        days, qtime = self.get_days_and_qtime_from_seconds(sim_config.timestamp_delay_sd)
        ui.time_delay_sd_time_input.setTime(qtime)
        ui.time_delay_sd_days_input.setValue(days)

        days, qtime = self.get_days_and_qtime_from_seconds(sim_config.timestamp_delay_min)
        ui.time_delay_minimum_time_input.setTime(qtime)
        ui.time_delay_minimum_days_input.setValue(days)

        days, qtime = self.get_days_and_qtime_from_seconds(sim_config.timestamp_delay_max)
        ui.time_delay_maximum_time_input.setTime(qtime)
        ui.time_delay_maximum_days_input.setValue(days)

        days, qtime = self.get_days_and_qtime_from_seconds(sim_config.avg_timestamp_lead)
        ui.avg_trans_lead_time_input.setTime(qtime)
        ui.avg_trans_lead_days_input.setValue(days)

        days, qtime = self.get_days_and_qtime_from_seconds(sim_config.timestamp_lead_sd)
        ui.time_lead_sd_time_input.setTime(qtime)
        ui.time_lead_sd_days_input.setValue(days)

        days, qtime = self.get_days_and_qtime_from_seconds(sim_config.timestamp_lead_min)
        ui.time_lead_minimum_time_input.setTime(qtime)
        ui.time_lead_minimum_days_input.setValue(days)

        days, qtime = self.get_days_and_qtime_from_seconds(sim_config.timestamp_lead_max)
        ui.time_lead_maximum_time_input.setTime(qtime)
        ui.time_lead_maximum_days_input.setValue(days)

        ui.include_invisible_transitions_input.setChecked(
            config.simulation_config.include_invisible_transitions_in_log)

        ui.duplicates_with_invisible_trans_input.setChecked(
            config.simulation_config.duplicates_with_invisible_trans)

        ui.timestamp_millieseconds_input.setChecked(
            config.simulation_config.timestamp_millieseconds)

        time_intervals_string = ""
        for time_interval in config.simulation_config.time_intervals:
            time_intervals_string += time_interval + ";\n"
        ui.time_intervals_input.setPlainText(time_intervals_string[:-2])
        ui.max_variance_input.setValue(config.simulation_config.max_time_interval_variance)
        ui.variance_input.setChecked(config.simulation_config.add_time_interval_variance)

        for trans_config in sim_config.transition_configs:
            self.update_trans_input_from_config(trans_config)

        for var_config in config.semantic_information:
            self.update_var_input_from_config(var_config)
        self.change_simulation_config_gui()

    def update_trans_input_from_config(self, trans_config: TransitionConfiguration):
        trans_input = self.get_trans_input_by_id(trans_config.transition_id)
        trans_input.activity_name_input.setText(trans_config.activity_name)
        trans_input.weight_input.setValue(trans_config.weight)
        trans_input.invisible_input.setChecked(self.main.model.get_place_or_transition_by_id(
            trans_config.transition_id).invisible)

        days, time = self.get_days_and_qtime_from_seconds(trans_config.avg_time_delay)
        trans_input.mean_delay_input[0].setValue(days)
        trans_input.mean_delay_input[1].setTime(time)

        days, time = self.get_days_and_qtime_from_seconds(trans_config.time_delay_sd)
        trans_input.delay_sd_input[0].setValue(days)
        trans_input.delay_sd_input[1].setTime(time)

        days, time = self.get_days_and_qtime_from_seconds(trans_config.time_delay_min)
        trans_input.delay_min_input[0].setValue(days)
        trans_input.delay_min_input[1].setTime(time)

        days, time = self.get_days_and_qtime_from_seconds(trans_config.time_delay_max)
        trans_input.delay_max_input[0].setValue(days)
        trans_input.delay_max_input[1].setTime(time)

        days, time = self.get_days_and_qtime_from_seconds(trans_config.lead_time_min)
        trans_input.lead_min_input[0].setValue(days)
        trans_input.lead_min_input[1].setTime(time)

        days, time = self.get_days_and_qtime_from_seconds(trans_config.lead_time_max)
        trans_input.lead_max_input[0].setValue(days)
        trans_input.lead_max_input[1].setTime(time)

        days, time = self.get_days_and_qtime_from_seconds(trans_config.avg_lead_time)
        trans_input.lead_mean_input[0].setValue(days)
        trans_input.lead_mean_input[1].setTime(time)

        days, time = self.get_days_and_qtime_from_seconds(trans_config.lead_time_sd)
        trans_input.lead_sd_input[0].setValue(days)
        trans_input.lead_sd_input[1].setTime(time)

        trans_input.general_config_input.setChecked(trans_config.use_general_config)

        trans_input.no_time_forwarding_input.setChecked(trans_config.no_time_forward)

        trans_input.variance_input.setChecked(trans_config.add_time_interval_variance)
        trans_input.max_variance_input.setValue(trans_config.max_time_interval_variance)
        time_intervals_string = ""
        for time_interval in trans_config.time_intervals:
            time_intervals_string += time_interval + ";\n"
        trans_input.time_intervals_input.setPlainText(time_intervals_string[:-2])

        for variable in self.main.model.variables:
            if variable.original_name in trans_config.included_vars:
                self.get_variable_checkbox_by_name(variable.original_name,
                                                   trans_input.included_vars) \
                    .setChecked(True)
            else:
                self.get_variable_checkbox_by_name(variable.original_name,
                                                   trans_input.included_vars) \
                    .setChecked(False)

    def get_trans_input_by_id(self, trans_id):
        for trans_input in self.transition_inputs:
            if trans_input.transition.id == trans_id:
                return trans_input
        return None

    def update_var_input_from_config(self, var_config: SemanticInformation):
        var_input = self.get_var_input_by_name(var_config.variable_name)

        variable = var_input.variable
        var_type = variable.type

        var_input.fixed_variable_input.setChecked(var_config.fixed_variable)
        var_input.trace_variable_input.setChecked(var_config.trace_variable)

        var_input.use_initial_value_input.setChecked(var_config.use_initial_value)
        var_input.gen_initial_value_input.setChecked(var_config.generate_initial_value)
        var_input.values_input.setPlainText(var_config.get_values_string(self.main.model))
        var_input.dependencies_input.setPlainText(var_config.get_dependencies_string(variable.type))

        if var_type in [VariableTypes.INT, VariableTypes.LONG, VariableTypes.DOUBLE]:

            var_input.inverse_intervals_input.setChecked(var_config.include_inverse_intervals)
            if var_type == VariableTypes.DOUBLE:
                var_input.self_deviation_input.setValue(var_config.self_reference_deviation)
                zero = 0.0
            else:
                var_input.self_deviation_input.setValue(int(var_config.self_reference_deviation))
                zero = 0
            var_input.initial_input.setValue(var_config.initial_value)
            if var_config.has_min:
                var_input.min_input.setValue(var_config.min)
            else:
                var_input.min_input.setValue(zero)
            if var_config.has_max:
                var_input.max_input.setValue(var_config.max)
            else:
                var_input.max_input.setValue(zero)
            var_input.info_used_input.setCurrentIndex(var_config.used_information)
            if var_config.has_distribution:
                if var_config.distribution.distribution_type == "uniform":
                    var_input.distributions_input.setCurrentIndex(0)
                elif var_config.distribution.distribution_type == "normal":
                    var_input.distributions_input.setCurrentIndex(1)
                elif var_config.distribution.distribution_type == "exponential":
                    var_input.distributions_input.setCurrentIndex(2)
                self.change_variable_input_widget_distribution(var_input,
                                                               var_input.distributions_input)
                if var_type == VariableTypes.DOUBLE:
                    var_input.distributions_mean_input.setValue(float(var_config.avg))
                    var_input.distributions_sd_input.setValue(float(var_config.sd))
                else:
                    var_input.distributions_mean_input.setValue(var_config.avg)
                    var_input.distributions_sd_input.setValue(var_config.sd)
            else:
                var_input.distributions_input.setCurrentIndex(0)
                var_input.distributions_sd_input.setValue(0)
                var_input.distributions_mean_input.setValue(0)
            var_input.intervals_input.setPlainText(var_config.get_intervals_string(self.main.model))
            if var_type == VariableTypes.DOUBLE:
                var_input.precision_input.setValue(var_config.precision)
        elif var_type == VariableTypes.BOOL:
            if var_config.initial_value:
                var_input.initial_input.setChecked(False)
                var_input.initial_input2.setChecked(True)
            else:
                var_input.initial_input.setChecked(True)
                var_input.initial_input2.setChecked(False)
        elif var_type == VariableTypes.STRING:
            var_input.initial_input.setText(var_config.initial_value)
        else:  # DATE
            days, time = self.get_days_and_qtime_from_seconds(
                int(var_config.self_reference_deviation))
            var_input.self_deviation_input.setValue(days)
            var_input.self_deviation_input2.setTime(time)

            var_input.inverse_intervals_input.setChecked(var_config.include_inverse_intervals)
            var_input.initial_input.setDateTime(QDateTime.fromSecsSinceEpoch(
                var_config.initial_value))
            var_input.min_input.setDateTime(QDateTime.fromString(
                "2000-01-01T00:00:00", "yyyy-MM-ddThh:mm:ss"))
            var_input.max_input.setDateTime(QDateTime.fromString(
                "2000-01-01T00:00:00", "yyyy-MM-ddThh:mm:ss"))
            if var_config.has_min:
                var_input.min_input.setDateTime(QDateTime.fromSecsSinceEpoch(var_config.min))
            if var_config.has_max:
                var_input.max_input.setDateTime(QDateTime.fromSecsSinceEpoch(var_config.max))
            var_input.info_used_input.setCurrentIndex(var_config.used_information)
            var_input.intervals_input.setPlainText(var_config.get_intervals_string(self.main.model))

            if var_config.has_distribution:
                if var_config.distribution.distribution_type == "uniform":
                    var_input.distributions_input.setCurrentIndex(0)
                elif var_config.distribution.distribution_type == "normal":
                    var_input.distributions_input.setCurrentIndex(1)
                elif var_config.distribution.distribution_type == "exponential":
                    var_input.distributions_input.setCurrentIndex(2)
                self.change_variable_input_widget_distribution(var_input,
                                                               var_input.distributions_input)
                var_input.distributions_mean_input.setDateTime(QDateTime.fromSecsSinceEpoch(
                    int(var_config.avg)))
                days, time = self.get_days_and_qtime_from_seconds(
                    var_config.sd)
                var_input.distributions_sd_input[0].setValue(days)
                var_input.distributions_sd_input[1].setTime(time)
            else:
                var_input.distributions_input.setCurrentIndex(0)
                var_input.distributions_mean_input.setDateTime(QDateTime.fromSecsSinceEpoch(
                    int(var_config.avg)))
                days, time = self.get_days_and_qtime_from_seconds(
                    var_config.sd)
                var_input.distributions_sd_input[0].setValue(days)
                var_input.distributions_sd_input[1].setTime(time)

    def get_var_input_by_name(self, name):
        for var_input in self.variable_inputs:
            if var_input.variable.original_name == name:
                return var_input
        return None

    def get_days_and_qtime_from_seconds(self, seconds):
        days, hours, minutes, seconds = self.get_days_hours_min_sec(seconds)
        return days, QTime(hours, minutes, seconds)

    def safe_config(self, file_path=None, only_safe=False):
        if self.status == Status.MODEL_LOADED:
            self.update_config_from_gui()
            self.main.config.model_file_path = self.main.model_path
        if file_path is None:
            file_path = QFileDialog.getSaveFileName(self.window, 'Safe configuration', os.getcwd(),
                                                    "JSON File (*.json)")[0]
        if file_path:
            if only_safe:
                try:
                    self.main.config.write_config_file(file_path)
                except:
                    self.display_error_msg(str(traceback.format_exc()),
                                           "An Error occurred while saving the configuration!")
            else:
                if self.status == Status.MODEL_LOADED or self.status == Status.SIM_RUNNING:
                    warnings = []
                    for var_input in self.variable_inputs:
                        warnings += self.check_values_config(var_input,
                                                             var_input.variable.original_name,
                                                             True)
                        warnings += self.check_dependencies_config(var_input,
                                                                   var_input.variable.original_name,
                                                                   True)
                        if var_input.variable.type in [VariableTypes.DATE, VariableTypes.INT
                            , VariableTypes.LONG, VariableTypes.DOUBLE]:
                            warnings += self.check_intervals_config(var_input,
                                                                    var_input.variable.original_name,
                                                                    True)
                    if warnings:
                        text = ""
                        for warning in warnings:
                            text += warning + "\n"
                        if text is None:
                            text = "An Error occurred!"
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Critical)
                        msg.setText("Saving the configuration failed with the following errors:\n")
                        msg.setWindowTitle("Error!")
                        msg.setInformativeText(text)
                        msg.setButtonText(1, "Ok")
                        msg.exec()
                    else:
                        self.update_config_from_gui()
                        self.main.config.write_config_file(file_path)
                else:
                    try:
                        self.main.config = Configuration(None)
                        self.update_config_from_gui()
                        self.main.config.write_config_file(file_path)
                    except:
                        self.display_error_msg(str(traceback.format_exc()),
                                               "An Error occurred while saving the configuration!")

    def change_variance_input(self):
        if self.window.ui.variance_input.isChecked():
            self.window.ui.max_variance_input.setEnabled(True)
        else:
            self.window.ui.max_variance_input.setEnabled(False)

    def change_perform_trace_estimation(self):
        if self.window.ui.trace_estimation_input.isChecked():
            self.window.ui.duplicates_with_data_input.setChecked(False)

    def change_duplicates_with_data(self):
        if self.window.ui.duplicates_with_data_input.isChecked():
            self.window.ui.trace_estimation_input.setChecked(False)

    def change_simulation_config_gui(self):
        sim_strat = self.window.ui.sim_strategy_input.currentIndex()
        self.window.ui.widget_4.setEnabled(True)
        for child in self.window.ui.sim_config.widget().children():
            if type(child) != QVBoxLayout:
                child.setHidden(False)
        ui = self.window.ui
        ui.changing_loop.setHidden(True)
        if sim_strat == 0:  # Random Trace Generation
            ui.changing_loop.setHidden(True)
            ui.nr_of_traces_label.setText("Nr. of Traces:")
            ui.nr_of_traces_label.setToolTip("<html><head/><body><p>The number of traces that will"
                                             " be generated for each event log.</p></body></html>")
            ui.widget_4.setEnabled(True)
            ui.include_partial_traces.setHidden(True)
            ui.trace_estimation.setHidden(True)
            ui.limit_variable_values.setHidden(True)
            ui.merge_intervals.setHidden(True)

        elif sim_strat == 1:  # Random Exploration
            ui = self.window.ui
            ui.limit_variable_values.setHidden(True)
            ui.merge_intervals.setHidden(True)
            ui.max_trace_duplicates.setHidden(True)
            ui.duplicates_with_data.setHidden(False)
            ui.nr_of_traces_label.setText("Max. Nr. of Traces:")
            ui.nr_of_traces_label.setToolTip("<html><head/><body><p>The maximum number of traces"
                                             " that will be generated.</p></body></html>")
            self.window.ui.widget_4.setEnabled(False)
            self.window.ui.nr_of_event_logs_input.setValue(1)
        else:  # All Traces
            ui.trace_estimation.setHidden(True)
            ui.nr_of_traces_label.setText("Max. Nr. of Traces:")
            ui.nr_of_traces_label.setToolTip("<html><head/><body><p>The maximum number of traces"
                                             " that will be generated.</p></body></html>")
            ui.widget_4.setEnabled(False)
            ui.max_trace_duplicates.setHidden(True)
            ui.duplicates_with_data.setHidden(True)
            ui.include_partial_traces.setHidden(False)

    def display_about_info(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.NoIcon)
        msg.setText("DPN Log Generator")
        msg.setInformativeText("Created by David Jilg")
        msg.setWindowTitle("About")
        msg.setButtonText(1, "Close")
        msg.exec()

    def open_user_manual(self):
        manual_path = os.getcwd() + "/src/documentation/manual.pdf"
        if os.name == 'nt':
            os.startfile(manual_path)
        else:
            wb.open_new(manual_path)
            # subprocess.call(["xdg-open", manual_path])
