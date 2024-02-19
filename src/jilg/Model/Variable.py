from typing import List, Union

from PySide6.QtCore import QDateTime

from src.jilg.Model.SemanticInformation import SemanticInformation
from src.jilg.Other.Global import print_summary_global, VariableTypes

'''
This class is used to represent all variables of the internal model representation.
'''


class Variable:
    has_current_value: bool
    name: str
    type: VariableTypes
    pos_x: float
    pos_y: float
    height: float
    width: float
    replacement: bool  # variables with invalid names get a replacement name
    original_name: str  # original name before a possible replacement
    has_been_written_to: bool
    has_initial_value: bool

    has_nex_value: bool  # Used for Prime variables in guard conditions
    next_value: List[tuple]

    numeric_types = [VariableTypes.INT, VariableTypes.DOUBLE, VariableTypes.LONG]
    semantic_information: SemanticInformation

    def print_summary(self, print_list_elements: bool = False):
        print_summary_global(self, print_list_elements)

    def reset(self):
        if self.semantic_information.use_initial_value:
            self.value = self.semantic_information.initial_value
            self.has_current_value = True
        else:
            self.has_current_value = False
        self.has_been_written_to = False
        self.has_nex_value = False
        self.next_value = []

    def get_next_value_string(self, transition) -> str:
        if self.type in [VariableTypes.INT, VariableTypes.LONG, VariableTypes.DOUBLE]:
            return f'{self.get_correct_next_value(transition.id)}'
        elif self.type == VariableTypes.STRING:
            return f'"{self.get_correct_next_value(transition.id)}"'
        elif self.type == VariableTypes.DATE:
            return QDateTime.fromSecsSinceEpoch(int(self.get_correct_next_value(transition.id))) \
                .toString(format="yyyy-MM-ddThh:mm:ss")
        elif self.type == VariableTypes.BOOL:
            if self.get_correct_next_value(transition.id):
                return "True"
            else:
                return "False"

    def get_correct_next_value(self, transition_id) -> Union[str, int, float, QDateTime]:
        for value in self.next_value:
            if value[0] == transition_id:
                return value[1]
        return "NONE"

    def get_next_value_transitions(self) -> [str]:
        transition_ids = []
        if self.has_nex_value:
            for next_value in self.next_value:
                transition_ids.append(next_value[0])
        return transition_ids

    def __init__(self, name: str, variable_type: str, pos_x: Union[None, str], pos_y: Union[None, str],
                 height: Union[None, int], width: Union[None, int],
                 min_value: Union[None, float, int, QDateTime], max_value: Union[None, float, int, QDateTime],
                 value, replacement=False):
        self.type = VariableTypes(variable_type)
        if value is not None:
            if self.type == VariableTypes.DATE:
                self.value = QDateTime.fromString(value, "yyyy-MM-ddThh:mm:ss").toSecsSinceEpoch()
            else:
                self.value = value
            self.has_initial_value = True
            self.initial_value = self.value
            self.has_current_value = True
        else:
            self.has_initial_value = False
            self.has_current_value = False
        self.name = name
        self.original_name = name

        self.pos_x = pos_x if pos_x is not None else -1
        self.pos_y = pos_y if pos_y is not None else -1
        self.height = height if height is not None else -1
        self.width = width if width is not None else -1
        if min_value is not None:
            if self.type == VariableTypes.INT:
                self.min_value = int(min_value)
            elif self.type == VariableTypes.DOUBLE:
                self.min_value = float(min_value)
            elif self.type == VariableTypes.DATE:
                self.min_value = QDateTime.fromString(min_value, "yyyy-MM-ddThh:mm:ss") \
                    .toSecsSinceEpoch()
            else:
                self.min_value = min_value
        else:
            self.min_value = None
        if max_value is not None:
            if self.type == VariableTypes.INT:
                self.max_value = int(max_value)
            elif self.type == VariableTypes.DOUBLE:
                self.max_value = float(max_value)
            elif self.type == VariableTypes.DATE:
                self.max_value = QDateTime.fromString(max_value, "yyyy-MM-ddThh:mm:ss") \
                    .toSecsSinceEpoch()
            else:
                self.max_value = max_value
        else:
            self.max_value = None

        self.replacement = replacement
        self.has_been_written_to = False
        self.has_nex_value = False
