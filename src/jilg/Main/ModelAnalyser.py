import logging
import re
import traceback
from typing import Union

from PySide6.QtCore import QDateTime

from src.jilg.Main.Configuration import Configuration
from src.jilg.Model.Model import Model
from src.jilg.Other import Global
from src.jilg.Other.Global import VariableTypes

'''
This class is used to analyse the guard conditions and identify valid values and intervals for the
variables that can be presented to the user to help him when he specifies the semantic information.

Consider the following exemplary guard string: "cancer_type == 'Lymphoma'"
In this case the ModelAnalyser would determine that 'Lymphoma' is a valid value for the variable
cancer_type.
'''


class ModelAnalyser:
    search_stop_operators_chars = [">", "<", "-", "+", "*", "/", "&", "|", "!", "<", ">", "(",
                                   ")"]
    numeric_var_types = [VariableTypes.INT, VariableTypes.LONG, VariableTypes.DOUBLE,
                         VariableTypes.DATE]

    def analyse_model(self, model: Model, config: Configuration):
        variable_names = []
        for variable in model.variables:
            variable_names.append(variable.name)
        self.determine_values(model, config, variable_names)
        self.determine_intervals(model, config, variable_names)

    def determine_intervals(self, model: Model, config: Configuration, var_names: [str], with_return: bool = False) ->\
            Union[None, dict[str]]:
        if var_names is None:
            var_names = []
            for variable in model.variables:
                var_names.append(variable.name)
        guards = []
        for transition in model.transitions:
            if transition.guard is not None:
                guards.append(transition.guard.guard_string)
        interval_dict = {}
        for var_name in var_names:
            if model.get_variable_by_name(var_name).type in self.numeric_var_types:
                interval_dict[var_name] = []

        for guard in guards:
            self.analyse_guard_intervals(guard, var_names, model, interval_dict)
        for key in interval_dict.keys():
            interval_list = list(dict.fromkeys(interval_dict[key]))
            variable_type = model.get_variable_by_name(key).type
            interval_list_with_parsed_numbers = []
            for interval in interval_list:
                if variable_type == VariableTypes.INT or variable_type == VariableTypes.LONG:
                    interval_list_with_parsed_numbers.append((interval[0], int(interval[1])))
                elif variable_type == VariableTypes.DOUBLE:
                    interval_list_with_parsed_numbers.append((interval[0], float(interval[1])))
                elif variable_type == VariableTypes.DATE:
                    interval_list_with_parsed_numbers. \
                        append((interval[0],
                                QDateTime.fromString(interval[1][1:-1], "yyyy-MM-ddThh:mm:ss").
                                toSecsSinceEpoch()))
                else:
                    interval_list_with_parsed_numbers.append(interval)
            interval_dict[key] = interval_list_with_parsed_numbers
        if with_return:
            return interval_dict
        else:
            for key in interval_dict.keys():
                sem_info = config.get_sem_info_by_variable_name(key)
                sem_info.intervals = interval_dict[key]

    def analyse_guard_intervals(self, guard_string: str, var_names: [str], model: Model, interval_dict: {str}):
        if "<" in guard_string or ">" in guard_string:
            for var_name in var_names:
                var = model.get_variable_by_name(var_name)
                if var.type in self.numeric_var_types:
                    if var_name in guard_string:
                        processed_guard = guard_string
                        for other_variable_name in var_names:
                            if other_variable_name != var_name:
                                processed_guard = processed_guard.replace(other_variable_name, "")
                            else:
                                processed_guard = processed_guard.replace(other_variable_name+"'",
                                                                          "")
                        intervals, intervals_found = self.check_for_intervals(processed_guard,
                                                                              var_name, var.type)
                        if intervals_found:
                            for interval in intervals:
                                interval_dict[var_name].append(interval)

    def check_for_intervals(self, guard_string: str, var_name: str, var_type: VariableTypes) -> ([(str, str)], bool):
        intervals_found = False
        indices = [m.start() for m in re.finditer(var_name, guard_string)]
        intervals = []
        for index in indices:
            interval, interval_found = self.check_variable_name_occurence_for_interval(
                index, guard_string, var_type)
            if interval_found:
                intervals.append(interval)
                intervals_found = True
        return intervals, intervals_found

    def check_variable_name_occurence_for_interval(self, index: int, guard: str, var_type: VariableTypes) ->\
            Union[tuple[None, bool], bool]:
        index_copy = index
        while index_copy >= 0:  # Check left
            if guard[index_copy] == "=":
                if guard[index_copy - 1] == ">":
                    return self.find_interval(index_copy - 2, "left", guard, ">=", var_type)
                elif guard[index_copy - 1] == "<":
                    return self.find_interval(index_copy - 2, "left", guard, "<=", var_type)
                else:
                    break
            elif guard[index_copy] == "<":
                return self.find_interval(index_copy - 1, "left", guard, "<", var_type)
            elif guard[index_copy] == ">":
                return self.find_interval(index_copy - 1, "left", guard, ">", var_type)
            elif guard[index_copy] in self.search_stop_operators_chars:
                break
            index_copy -= 1
        index_copy = index
        while index_copy < len(guard):  # Check Right
            if guard[index_copy] == ">":
                if guard[index_copy + 1] != "=":
                    return self.find_interval(index_copy + 1, "right", guard, ">", var_type)
                elif guard[index_copy + 1] == "=":
                    return self.find_interval(index_copy + 2, "right", guard, ">=", var_type)
                else:
                    break
            elif guard[index_copy] == "<":
                if guard[index_copy + 1] != "=":
                    return self.find_interval(index_copy + 1, "right", guard, "<", var_type)
                elif guard[index_copy + 1] == "=":
                    return self.find_interval(index_copy + 2, "right", guard, "<=", var_type)
                else:
                    break
            elif guard[index_copy] in self.search_stop_operators_chars:
                break
            index_copy += 1
        return None, False

    def find_interval(self, index: int, direction: str, guard: str, operator: str, var_type: VariableTypes) ->\
            Union[tuple[None, bool], tuple[tuple[str, str], bool]]:
        interval_boundry_str = ""
        minus_counter = 0
        if direction == "left":
            while index >= 0:
                if guard[index] in self.search_stop_operators_chars:
                    if guard[index] == "-" and var_type == VariableTypes.DATE:
                        minus_counter += 1
                        if minus_counter > 2:
                            break
                        else:
                            interval_boundry_str = guard[index] + interval_boundry_str
                            index -= 1
                    else:
                        break
                else:
                    interval_boundry_str = guard[index] + interval_boundry_str
                    index -= 1
            if interval_boundry_str and not interval_boundry_str.isspace():
                return (self.invert_operator(operator), interval_boundry_str), True
        else:  # Right
            while index < len(guard):
                if guard[index] in self.search_stop_operators_chars:
                    if guard[index] == "-" and var_type == VariableTypes.DATE:
                        minus_counter += 1
                        if minus_counter > 2:
                            break
                        else:
                            interval_boundry_str = interval_boundry_str + guard[index]
                            index += 1
                    else:
                        break
                else:
                    interval_boundry_str = interval_boundry_str + guard[index]
                    index += 1
            if interval_boundry_str and not interval_boundry_str.isspace():
                return (operator, interval_boundry_str), True
        return None, False

    def invert_operator(self, operator: str) -> str:
        if operator == "<":
            return ">"
        elif operator == ">":
            return "<"
        elif operator == "<=":
            return ">="
        elif operator == ">=":
            return "<="
        else:
            return operator

    def determine_values(self, model: Model, config: Configuration, variable_names: [str]):
        guards = []
        for transition in model.transitions:
            if transition.guard is not None:
                guards.append(transition.guard.guard_string)
        for guard in guards:
            self.analyse_guard(guard, variable_names, config, model)
        config.remove_duplicate_variable_values()
        config.configure_variables_and_transitions(model)

    def analyse_guard(self, guard: str, variable_names: [str], config: Configuration, model: Model):
        for variable_name in variable_names:
            if variable_name in guard:
                processed_guard = guard
                for other_variable_name in variable_names:
                    if other_variable_name != variable_name:
                        processed_guard.replace(other_variable_name, "")
                    else:
                        processed_guard = processed_guard.replace(other_variable_name + "'", "")
                values, values_found = self.check_for_values(processed_guard, variable_name)
                if values_found:
                    self.add_values(values, variable_name, config, model)

    def check_for_values(self, guard: str, variable_name: str) -> (list, bool):
        values = []
        values_found = False
        indices = [m.start() for m in re.finditer(variable_name, guard)]
        for index in indices:
            value, value_found = self.check_variable_name_occurence_for_value(index, variable_name,
                                                                              guard)
            if value_found:
                values.append(value)
                values_found = True
        return values, values_found

    def check_variable_name_occurence_for_value(self, index: int, variable_name: str, guard: str) -> (str, bool):
        index_copy = index
        while index_copy >= 0:
            if guard[index_copy] == "=":
                if guard[index_copy - 1] == "=":
                    return self.find_value(index_copy - 2, "left", guard)
                else:
                    break
            elif guard[index_copy] in self.search_stop_operators_chars:
                break
            index_copy -= 1
        index_copy = index + len(variable_name)
        while index_copy < len(guard):
            if guard[index_copy] == "=":
                if guard[index_copy + 1] == "=":
                    return self.find_value(index_copy + 2, "right", guard)
                else:
                    return "", False
            elif guard[index_copy] in self.search_stop_operators_chars:
                return "", False
            index_copy += 1

    def find_value(self, index: int, search_direction: str, guard_string: str) -> (str, bool):
        value = ""
        if search_direction == "left":
            while index >= 0:
                if guard_string[index] in self.search_stop_operators_chars:
                    break
                else:
                    value = guard_string[index] + value
                index -= 1
        else:
            while index < len(guard_string):
                if guard_string[index] in self.search_stop_operators_chars:
                    break
                else:
                    value = value + guard_string[index]
                index += 1
        if len(value.replace(" ", "")) < 1:
            return "", False
        else:
            if "false" in value:
                return "false", True
            elif "true" in value:
                return "true", True
            elif "'" in value:
                return value.split("'")[1], True
            elif '"' in value:
                return value.split('"')[1], True
            else:
                return value.replace(" ", ""), True

    def add_values(self, values: list, variable_name: str, config: Configuration, model: Model):
        sem_info = config.get_sem_info_by_variable_name(variable_name)
        variable_type = model.get_variable_by_name(variable_name).type
        if variable_type == VariableTypes.DATE or variable_type == VariableTypes.STRING:
            for value in values:
                sem_info.values[0].append(value)
                sem_info.values[1].append(1)
        elif variable_type == VariableTypes.INT or variable_type == VariableTypes.LONG:
            for value in values:
                try:
                    sem_info.values[0].append(int(value))
                    sem_info.values[1].append(1)
                except:
                    Global.log_error(__file__, "Adding integer values to sem info"
                                                              " object failed!", traceback)
        elif variable_type == VariableTypes.DOUBLE:
            for value in values:
                try:
                    sem_info.values[0].append(float(value))
                    sem_info.values[1].append(1)
                except:
                    Global.log_error(__file__, "Adding float values to sem info"
                                                              " object failed!", traceback)
        else:
            for value in values:
                if value in ["true", "True", "TRUE"]:
                    sem_info.values[0].append(True)
                    sem_info.values[1].append(1)
                else:
                    sem_info.values[0].append(False)
                    sem_info.values[1].append(1)
