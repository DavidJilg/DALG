import math

import numpy as np

from src.jilg.Model.MilpSolver import MilpSolver
from src.jilg.Model.Model import Model
from src.jilg.Other.Global import VariableTypes
from src.jilg.Other.Global import print_summary_global

'''
This class is used to generate variable values if a transition writes to a variable during the
simulation.
'''


class ValueGenerator:
    model: Model
    rng: np.random.default_rng
    milp_solver: MilpSolver
    number_of_tries: int

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)

    def __init__(self, model, rng):
        self.model = model
        self.rng = rng
        self.milp_solver = MilpSolver()
        self.number_of_tries = 10

    def generate_variable_values(self, transition):
        written_variables = []
        written_variables_tmp = []
        written_variables_with_out_dependency = []
        for variable in transition.writes_variables:
            if len(variable.semantic_information.dependencies) == 0:
                written_variables_with_out_dependency.append(variable)
            else:
                written_variables_tmp.append((len(variable.semantic_information.dependencies),
                                              variable))
        written_variables_tmp.sort(key=lambda x: x[0])
        for variable in written_variables_tmp:
            written_variables.append(variable[1])
        written_variables = written_variables_with_out_dependency + written_variables
        for variable in written_variables:
            if variable.semantic_information.fixed_variable:
                if not variable.has_been_written_to:
                    variable.value = self.generate_variable_value(variable, transition)
                    variable.has_current_value = True
                    variable.has_been_written_to = True
            else:
                variable.value = self.generate_variable_value(variable, transition)
                variable.has_current_value = True
                variable.has_been_written_to = True

    def add_deviation(self, deviation_max):
        if deviation_max == 0 or deviation_max == 0.0:
            return 0
        else:
            return self.rng.uniform(0 - deviation_max, deviation_max)

    def generate_self_reference_value(self, dependency, variable, transition):
        constraint = dependency[1]
        operator = constraint[0]
        if operator == "==":
            if constraint[1] == "_EVENT_NAME_":
                return transition.config.activity_name
            else:
                var = self.model.get_variable_by_name(constraint[1])
                if var.has_current_value:
                    return variable.value
                else:
                    return self.replacement_value(variable)
        else:
            op_value = constraint[1] + self.add_deviation(variable.semantic_information.
                                                          self_reference_deviation)
            if variable.type in [VariableTypes.INT, VariableTypes.LONG, VariableTypes.DATE]:
                op_value = round(op_value)
            if operator == "+":
                value = variable.value + op_value
            elif operator == "-":
                value = variable.value - op_value
            elif operator == "/":
                value = variable.value / op_value
            else:  # *
                value = variable.value * op_value
            if variable.type in [VariableTypes.INT, VariableTypes.LONG, VariableTypes.DATE]:
                value = round(value)

            if value > variable.semantic_information.max:
                return variable.semantic_information.max
            elif value < variable.semantic_information.min:
                return variable.semantic_information.min
            else:
                if variable.type == VariableTypes.DOUBLE:
                    return round(value, variable.semantic_information.precision)
                else:
                    return value

    def generate_variable_value(self, variable, transition):
        dependencies = variable.semantic_information.dependencies
        invalid_values = []
        if dependencies:
            constraints = self.evaluate_dependencies(dependencies, self.model)
            if constraints:
                interval_constraints, equal_constraints, not_equal_constraints = \
                    self.sort_constraints(constraints)
                if equal_constraints:
                    for i in range(10):
                        value = self.choose_equal_constraint(equal_constraints)
                        if value not in invalid_values:
                            if variable.type == VariableTypes.DOUBLE:
                                return round(value, variable.semantic_information.precision)
                            else:
                                return value
                    value = self.choose_equal_constraint(equal_constraints)
                    if variable.type == VariableTypes.DOUBLE:
                        return round(value, variable.semantic_information.precision)
                    else:
                        return value
                elif interval_constraints:
                    if not_equal_constraints:
                        for constraint in not_equal_constraints:
                            invalid_values.append(constraint[1])
                    interval, in_bounds = self.get_merged_constraint_interval(interval_constraints,
                                                                              variable)
                    if in_bounds:
                        for i in range(self.number_of_tries):
                            value = self.choose_interval_value(variable, interval)
                            if value not in invalid_values:
                                return value
                        return self.choose_interval_value(variable, interval)
                elif not_equal_constraints:
                    for constraint in not_equal_constraints:
                        invalid_values.append(constraint[1])
        if variable.has_current_value:
            for dependency in dependencies:
                if dependency[0] in ["SELF_REFERENCE", "self", "SELF",
                                     "self_reference", "Self_Reference"]:
                    return self.generate_self_reference_value(dependency, variable, transition)
        if variable.semantic_information.used_information == 0:
            value = self.choose_value(variable, invalid_values)
            if variable.type == VariableTypes.DOUBLE:
                return round(value, variable.semantic_information.precision)
            else:
                return value

        elif variable.semantic_information.used_information == 2:
            if variable.type in [VariableTypes.INT, VariableTypes.LONG]:
                for i in range(self.number_of_tries):
                    value = variable.semantic_information.distribution.get_next_int()
                    if value not in invalid_values:
                        return value
                return variable.semantic_information.distribution.get_next_int()
            else:
                for i in range(self.number_of_tries):
                    value = variable.semantic_information.distribution.get_next_float()
                    if value not in invalid_values:
                        if variable.type == VariableTypes.DOUBLE:
                            return round(value, variable.semantic_information.precision)
                        else:
                            return value
                value = variable.semantic_information.distribution.get_next_float()
                if variable.type == VariableTypes.DOUBLE:
                    return round(value, variable.semantic_information.precision)
                else:
                    return value

        else:
            for i in range(self.number_of_tries):
                value = self.choose_interval_value(variable, None)
                if value not in invalid_values:
                    return value
            return self.choose_interval_value(variable, None)

    def get_merged_constraint_interval(self, intervals, variable):
        min = variable.semantic_information.min
        max = variable.semantic_information.max

        if variable.type == VariableTypes.DOUBLE:
            offset = 0.0000000000000001
        else:
            offset = 1
        if len(intervals) == 1:
            if intervals[0][0] == "<":
                interval = (min, intervals[0][1] - offset)
            elif intervals[0][0] == ">":
                interval = (intervals[0][1] + offset, max)
            elif intervals[0][0] == "<=":
                interval = (min, intervals[0][1])
            else:  # intervals[0][0] == ">=":
                interval = (intervals[0][1], max)
            return interval, self.check_if_in_bounds(interval, variable)
        else:
            min_tmp, max_tmp = min, max
            for interval in intervals:
                value = interval[1]
                operator = interval[0]
                if operator == "<":
                    if not max_tmp <= value - offset:
                        max_tmp = value - offset
                elif operator == ">":
                    if not min_tmp > value:
                        min_tmp = value + offset
                elif operator == "<=":
                    if not max_tmp <= value:
                        max_tmp = value
                else:  # intervals[0][0] == ">=":
                    if not min_tmp >= value:
                        min_tmp = value
            if max_tmp - min_tmp > 0:
                return (min_tmp, max_tmp), self.check_if_in_bounds((min_tmp, max_tmp), variable)
            else:
                return (min, max), self.check_if_in_bounds((min, max), variable)

    def check_if_in_bounds(self, interval, variable):
        min = variable.semantic_information.min
        max = variable.semantic_information.max

        if interval[0] < min or interval[1] > max or interval[1] - interval[0] < 0:
            return False
        else:
            return True

    def choose_equal_constraint(self, constraints):
        index = self.rng.choice(range(len(constraints)))
        return constraints[index][1]

    def sort_constraints(self, constraints):
        interval_constraints, equal_constraints, not_equal_constraints = ([], [], [])
        for constraint in constraints:
            if constraint[0] == "==":
                equal_constraints.append(constraint)
            elif constraint[0] == "!=":
                not_equal_constraints.append(constraint)
            else:
                interval_constraints.append(constraint)
        return interval_constraints, equal_constraints, not_equal_constraints

    def evaluate_dependencies(self, dependencies, model):
        constraints = []
        for dependency in dependencies:
            if dependency[0] not in ["SELF_REFERENCE", "self", "SELF",
                                     "self_reference", "Self_Reference"]:
                fixed_dependency = self.replace_variable_names(dependency[0], model)
                read_variables = []
                for variable in model.variables:
                    if variable.name in fixed_dependency:
                        read_variables.append(variable)
                if self.evaluate_logical_expression(fixed_dependency, read_variables):
                    constraints.append(dependency[1])
        return constraints

    def replace_variable_names(self, guard_string, model):
        var_names = []
        var_original_names = []
        variables = []
        for variable in model.variables:
            if variable.replacement:
                var_names.append(variable.name)
                var_original_names.append(variable.original_name)
                variables.append(variable)
        replacement_vars = list(zip(var_original_names, var_names, variables))
        replacement_vars.sort(key=lambda s: len(s[0]))
        replacement_vars.reverse()
        for var in replacement_vars:
            guard_string = guard_string.replace(var[0], var[1])
        return guard_string

    def evaluate_logical_expression(self, logic_str, read_variables):
        return self.milp_solver.compile_and_evaluate_string(logic_str, read_variables)

    def choose_interval_value(self, variable, interval=None):
        if interval is not None:
            if interval[0] == interval[1]:
                if variable.type == VariableTypes.DOUBLE:
                    return round(interval[0], variable.semantic_information.precision)
                else:
                    return interval[0]
            if variable.type == VariableTypes.DOUBLE:
                return round(self.rng.uniform(interval[0], interval[1]),
                             variable.semantic_information.precision)
            else:
                return int(self.rng.uniform(interval[0], interval[1]))
        else:
            if variable.semantic_information.intervals:
                if variable.semantic_information.include_inverse_intervals:
                    intervals = self.get_inverse_intervals(variable.semantic_information.intervals)
                else:
                    intervals = variable.semantic_information.intervals
                intervals = self.check_if_intervals_are_in_bounds(intervals, variable)
                if intervals:
                    index = self.rng.choice(range(len(intervals)))
                    interval = intervals[index]
                    sem_info = variable.semantic_information
                    if interval[0] == "<":
                        if variable.type in [VariableTypes.INT, VariableTypes.LONG,
                                             VariableTypes.DATE]:
                            return math.floor(self.rng.uniform(sem_info.min, int(interval[1]) - 1))
                        else:  # variable.type == VariableTypes.DOUBLE:
                            return self.round_down(
                                self.rng.uniform(sem_info.min, float(interval[1])
                                                 - 0.0000000000000001),
                                variable.semantic_information.precision)
                    elif interval[0] == "<=":
                        if variable.type in [VariableTypes.INT, VariableTypes.LONG,
                                             VariableTypes.DATE]:
                            return round(self.rng.uniform(sem_info.min, int(interval[1])))
                        else:  # variable.type == VariableTypes.DOUBLE:
                            return round(self.rng.uniform(sem_info.min, float(interval[1])),
                                         variable.semantic_information.precision)
                    elif interval[0] == ">":
                        if variable.type in [VariableTypes.INT, VariableTypes.LONG,
                                             VariableTypes.DATE]:
                            return math.floor(self.rng.uniform(int(interval[1]) + 1, sem_info.max))
                        else:  # variable.type == VariableTypes.DOUBLE:
                            return self.round_up(
                                self.rng.uniform(float(interval[1]) + 0.0000000000000001,
                                                 sem_info.max),
                                variable.semantic_information.precision)
                    else:  # ">="
                        if variable.type in [VariableTypes.INT, VariableTypes.LONG,
                                             VariableTypes.DATE]:
                            return round(self.rng.uniform(int(interval[1]), sem_info.max))
                        else:  # variable.type == VariableTypes.DOUBLE:
                            return round(self.rng.uniform(float(interval[1]), sem_info.max),
                                         variable.semantic_information.precision)
                else:
                    return self.replacement_value(variable)
            else:
                return self.replacement_value(variable)

    def check_if_intervals_are_in_bounds(self, intervals, variable):
        valid_intervals = []
        sem_info = variable.semantic_information
        for interval in intervals:
            if interval[0] == "<":
                min = sem_info.min
                if variable.type in [VariableTypes.INT, VariableTypes.LONG, VariableTypes.DATE]:
                    max = int(interval[1]) - 1
                else:
                    max = float(interval[1]) - 0.0000000000000001
            elif interval[0] == "<=":
                min = sem_info.min
                if variable.type in [VariableTypes.INT, VariableTypes.LONG, VariableTypes.DATE]:
                    max = int(interval[1])
                else:
                    max = float(interval[1])

            elif interval[0] == ">":
                max = sem_info.max
                if variable.type in [VariableTypes.INT, VariableTypes.LONG, VariableTypes.DATE]:
                    min = int(interval[1]) + 1
                else:  # variable.type == VariableTypes.DOUBLE:
                    min = float(interval[1]) + 0.0000000000000001
            else:  # ">="
                max = sem_info.max
                if variable.type in [VariableTypes.INT, VariableTypes.LONG, VariableTypes.DATE]:
                    min = int(interval[1])
                else:  # variable.type == VariableTypes.DOUBLE:
                    min = float(interval[1])
            if max - min > 0 and max <= variable.semantic_information.max and \
                    min >= variable.semantic_information.min:
                valid_intervals.append(interval)
        return valid_intervals

    def round_up(self, value, precision):
        if precision == 0:
            return math.ceil(value)
        else:
            precision_factor = int("1" + ("0" * precision))
            int_value = value * precision_factor
            int_value = math.ceil(int_value)
            return int_value / precision_factor

    def round_down(self, value, precision):
        if precision == 0:
            return math.floor(value)
        else:
            precision_factor = int("1" + ("0" * precision))
            int_value = value * precision_factor
            int_value = math.floor(int_value)
            return int_value / precision_factor

    def get_inverse_intervals(self, intervals, only_inverse=False):
        inverse_intervals = []

        for interval in intervals:
            if interval[0] == "<":
                inverse_intervals.append((">=", interval[1]))
            elif interval[0] == ">":
                inverse_intervals.append(("<=", interval[1]))
            elif interval[0] == "<=":
                inverse_intervals.append((">", interval[1]))
            else:  # ">="
                inverse_intervals.append(("<", interval[1]))
        if only_inverse:
            return inverse_intervals
        else:
            return intervals + inverse_intervals

    def choose_value(self, variable, invalid_values=None):
        if invalid_values is None:
            invalid_values = []
        possible_values = []
        weights = []
        if variable.semantic_information.values[1]:
            for value, weight in zip(variable.semantic_information.values[0],
                                     variable.semantic_information.values[1]):
                if value not in invalid_values:
                    possible_values.append(value)
                    weights.append(weight)
        else:
            for value in variable.semantic_information.values[0]:
                if value not in invalid_values:
                    possible_values.append(value)
        if possible_values:
            if weights:
                value = self.rng.choice(a=possible_values,
                                        size=1, p=self.calculate_probs(weights))[0]
            else:
                value = self.rng.choice(possible_values, 1)[0]
            if value in ["false", "False", "FALSE"]:
                return False
            elif value in ["true", "True", "TRUE"]:
                return True
            else:
                return value
        else:
            return self.replacement_value(variable)

    def calculate_probs(self, weights):
        weights_copy = weights[:]
        probabilities = []
        if sum(weights_copy) == 0:
            new_weights = []
            for _weight in weights_copy:
                new_weights.append(1)
            weights_copy = new_weights
        factor = (1 / sum(weights_copy))
        for weight in weights_copy:
            probabilities.append(weight * factor)

        # accounting for floating point error, probabilities must sum up to 1 for numpy.choice
        probabilities_sum = sum(probabilities)
        if probabilities_sum > 1:
            probabilities[-1] -= probabilities_sum - 1
        elif probabilities_sum < 1:
            probabilities[-1] += 1 - probabilities_sum
        return probabilities

    def replacement_value(self, variable):
        if variable.type == VariableTypes.DATE:
            return int(self.rng.uniform(variable.semantic_information.min,
                                        variable.semantic_information.max))
        elif variable.type in [VariableTypes.INT, VariableTypes.LONG]:
            return int(self.rng.uniform(variable.semantic_information.min,
                                        variable.semantic_information.max))
        elif variable.type == VariableTypes.STRING:
            return "__NO_VALUES_DEFINED__"
        elif variable.type == VariableTypes.BOOL:
            return False
        elif variable.type == VariableTypes.DOUBLE:
            return float(self.rng.uniform(variable.semantic_information.min,
                                          variable.semantic_information.max))
