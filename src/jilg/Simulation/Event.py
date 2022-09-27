from PySide6.QtCore import QDateTime

from src.jilg.Other.Global import VariableTypes
from src.jilg.Other.Global import print_summary_global

'''
This class is used to represent events in the generated event log.
'''


class Event:
    name: str
    trans_id: str
    variables: list  # ("var_name", var_value, "var_type"), includes event timestamp
    from_invisible_transition: bool

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)

    def __init__(self, name, timestamp, model, trans_id, include_millieseconds, invisible=False):
        self.name = name
        self.trans_id = trans_id
        if not include_millieseconds:
            self.variables = [("time:timestamp", timestamp.replace(microsecond=0).isoformat(),
                               "date")]
        else:
            self.variables = [("time:timestamp", timestamp.isoformat(), "date")]
        self.from_invisible_transition = invisible
        for variable in model.variables:
            if variable.has_current_value and not variable.semantic_information.trace_variable:
                if variable.original_name in model.get_place_or_transition_by_id(
                        trans_id).config.included_vars:
                    if variable.type == VariableTypes.DATE:
                        try:
                            date = (QDateTime.fromSecsSinceEpoch(
                                int(variable.value)).toPython()).isoformat()
                        except:
                            date = "2000-01-01T00:00:00+00:00"
                        self.variables.append((variable.original_name, date,
                                               self.get_xml_variable_type_string(variable.type)))
                    else:
                        if variable.type == VariableTypes.DOUBLE:
                            self.variables.append((variable.original_name,
                                                   round(variable.value,
                                                         variable.semantic_information.precision),
                                                   self.get_xml_variable_type_string(
                                                       variable.type)))
                        else:
                            self.variables.append((variable.original_name, variable.value,
                                                   self.get_xml_variable_type_string(
                                                       variable.type)))

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
