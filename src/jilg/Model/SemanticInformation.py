from PySide6.QtCore import QDateTime

from src.jilg.Model import Distribution
from src.jilg.Other import Global
from src.jilg.Other.Global import print_summary_global, VariableTypes

'''
This class is used to store semantic information about variables, such as dependencies or intervals.
Each variable gets assigned one instance of this class.
'''


class SemanticInformation:
    variable_name: str
    original_variable_name: str
    fixed_variable: bool
    trace_variable: bool
    has_distribution: bool
    dependencies: list
    self_reference_deviation: float
    values: list
    intervals: list
    has_min: bool
    has_max: bool
    has_sd: bool
    has_avg: bool
    used_information: int  # 0=values, 1=intervals, 2=distribution
    distribution: Distribution
    use_initial_value: bool
    include_inverse_intervals: bool
    precision: int
    generate_initial_value: bool

    def print_summary(self, print_list_elements: bool = False):
        print_summary_global(self, print_list_elements)

    def __init__(self, variable, model):
        self.self_reference_deviation = 0.0
        self.fixed_variable = False
        self.trace_variable = False
        self.variable_name = variable.name
        self.original_variable_name = variable.original_name
        variable = model.get_variable_by_name(variable.name)
        if variable.has_current_value:
            self.initial_value = variable.value
        else:
            if variable.type in [VariableTypes.LONG, VariableTypes.INT, VariableTypes.DOUBLE]:
                if variable.type == VariableTypes.DOUBLE:
                    self.initial_value = float(0.0)
                else:
                    self.initial_value = int(0)
            elif variable.type == VariableTypes.STRING:
                self.initial_value = ""
            elif variable.type == VariableTypes.BOOL:
                self.initial_value = False
            else:
                self.initial_value = QDateTime.fromString("2000-01-01T00:00:00",
                                                          "yyyy-MM-ddThh:mm:ss").toSecsSinceEpoch()
        if variable.type in [VariableTypes.LONG, VariableTypes.INT]:
            self.max = int(0.0)
            self.min = int(1.0)
            self.has_max = True
            self.has_min = True
            self.has_sd = True
            self.has_avg = True
            self.sd = 1
            self.avg = 0
        elif variable.type == VariableTypes.DOUBLE:
            self.max = float(0.0)
            self.min = float(1.0)
            self.has_max = True
            self.has_min = True
            self.has_sd = True
            self.has_avg = True
            self.sd = 1
            self.avg = 0
        elif variable.type == VariableTypes.STRING:
            self.has_max = False
            self.has_min = False
            self.has_sd = False
            self.has_avg = False
        elif variable.type == VariableTypes.BOOL:
            self.has_max = False
            self.has_min = False
            self.has_sd = False
            self.has_avg = False
        else:
            self.min = QDateTime.fromString("2000-01-01T00:00:00",
                                            "yyyy-MM-ddThh:mm:ss").toSecsSinceEpoch()
            self.max = QDateTime.fromString("2001-01-01T00:00:00",
                                            "yyyy-MM-ddThh:mm:ss").toSecsSinceEpoch()
            self.has_max = True
            self.has_min = True
            self.has_sd = True
            self.has_avg = True
            self.sd = 1
            self.avg = QDateTime.fromString("2000-01-01T00:00:00",
                                            "yyyy-MM-ddThh:mm:ss").toSecsSinceEpoch()

        self.has_distribution = False
        self.values = [[], []]
        self.dependencies = []
        self.intervals = []
        self.distribution = None
        self.used_information = 0
        self.use_initial_value = False
        self.generate_initial_value = False
        self.include_inverse_intervals = False
        self.precision = Global.standard_precision

    def get_intervals_string(self, model) -> str:
        string = ""
        var_type = model.get_variable_by_name(self.variable_name).type
        for interval in self.intervals:
            if var_type == VariableTypes.DATE:
                date = QDateTime.fromSecsSinceEpoch(int(interval[1])).toString("yyyy-MM-ddThh:mm:ss")
                string += '("{operator}"; "{boundry}"),'.format(operator=interval[0],
                                                                boundry=date)
            else:

                string += '("{operator}"; "{boundry}"),'.format(operator=interval[0],
                                                                boundry=str(interval[1]))

        return string[:-1]

    def get_dependencies_string(self, var_type: VariableTypes = VariableTypes.STRING) -> str:
        string = ""
        for dependency in self.dependencies:
            logical_expression = str(dependency[0])
            operator = str(dependency[1][0])
            if var_type == VariableTypes.DATE:
                if logical_expression in ["SELF_REFERENCE", "self", "SELF",
                                          "self_reference", "Self_Reference"]:
                    if operator == "==":
                        value = dependency[1][1]
                    else:
                        value = self.get_self_reference_value(dependency[1][1])
                else:
                    value = QDateTime.fromSecsSinceEpoch(int(dependency[1][1])) \
                        .toString("yyyy-MM-ddThh:mm:ss")
            else:
                value = str(dependency[1][1])

            string += '"{logic}" => "\'{op}\'; \'{value}\'",\n'.format(logic=logical_expression,
                                                                       op=operator,
                                                                       value=value)
        return string[:-2]

    def get_self_reference_value(self, timestamp: int) -> str:
        days = timestamp // (24 * 3600)
        timestamp = timestamp % (24 * 3600)
        hours = timestamp // 3600
        timestamp %= 3600
        minutes = timestamp // 60
        timestamp %= 60
        seconds = timestamp
        string = ""
        if days < 10:
            string += "0"
        string += str(days) + ":"

        if hours < 10:
            string += "0"
        string += str(hours) + ":"

        if minutes < 10:
            string += "0"
        string += str(minutes) + ":"

        if seconds < 10:
            string += "0"
        string += str(seconds)
        return string

    def get_values_string(self, model) -> str:
        string = ""
        if model.get_variable_by_name(self.variable_name).type == VariableTypes.DATE:
            for value in self.values[0]:
                string += '"' + str(QDateTime.fromSecsSinceEpoch(int(value)).toPython()).replace(" ","T") + '"' + ', '
            values_part = string[:-2]
        else:
            for value in self.values[0]:
                string += '"' + str(value) + '", '
            values_part = string[:-2]
        if self.values[1]:
            values_part += " | "
            weight_part = ""
            for weight in self.values[1]:
                weight_part += str(weight) + ", "
            return values_part + weight_part[:-2]
        else:
            return values_part

    def remove_value_duplicates(self):
        new_value_list = []
        new_weight_list = []
        if self.values[1]:
            for value, weight in zip(self.values[0], self.values[1]):
                if value not in new_value_list:
                    new_value_list.append(value)
                    new_weight_list.append(weight)
        else:
            for value in self.values[0]:
                if value not in new_value_list:
                    new_value_list.append(value)
        self.values = [new_value_list, new_weight_list]
