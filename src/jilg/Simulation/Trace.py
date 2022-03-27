from PySide6.QtCore import QDateTime

from src.jilg.Other.Global import print_summary_global, VariableTypes


class Trace:
    name: str
    events: list
    variables: list  # ("var_name", var_value, "var_type")

    def add_trace_variables(self, model):
        for variable in model.variables:
            if variable.has_current_value and variable.semantic_information.trace_variable:
                if variable.type == VariableTypes.DATE:
                    date = (QDateTime.fromSecsSinceEpoch(variable.value).toPython()).isoformat()
                    self.variables.append((variable.original_name, date,
                                           self.get_xml_variable_type_string(variable.type)))
                else:
                    if variable.type == VariableTypes.DOUBLE:
                        self.variables.append((variable.original_name,
                                               round(variable.value,
                                                     variable.semantic_information.precision),
                                               self.get_xml_variable_type_string(variable.type)))
                    else:
                        self.variables.append((variable.original_name, variable.value,
                                               self.get_xml_variable_type_string(variable.type)))

    def truncate(self, f, n):
        s = '{}'.format(f)
        if 'e' in s or 'E' in s:
            return '{0:.{1}f}'.format(f, n)
        i, p, d = s.partition('.')
        return '.'.join([i, (d + '0' * n)[:n]])

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)

    def to_string(self):
        string = self.name + ": "
        for event in self.events:
            string += ", "+event.name
        return string

    def get_transition_ids(self):
        trans_ids = []
        for event in self.events:
            trans_ids.append(event.trans_id)
        return trans_ids

    def __init__(self, name):
        self.name = name
        self.events = []
        self.variables = []


    def get_xml_variable_type_string(self, var_type):
        if var_type == VariableTypes.DATE:
            return "date"
        elif var_type == VariableTypes.LONG or var_type == VariableTypes.INT:
            return "int"
        elif var_type == VariableTypes.STRING:
            return "string"
        elif var_type == VariableTypes.BOOL:
            return "boolean"
        elif var_type == VariableTypes.DOUBLE:
            return "float"