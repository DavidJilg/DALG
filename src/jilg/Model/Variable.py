from PySide6.QtCore import QDateTime

from src.jilg.Model.SemanticInformation import SemanticInformation
from src.jilg.Other.Global import print_summary_global, VariableTypes


class Variable:
    has_current_value: bool
    name: str
    type: VariableTypes
    pos_x: float
    pos_y: float
    height: float
    width: float
    replacement: bool
    original_name: str
    has_been_written_to: bool
    has_initial_value: bool

    numeric_types = [VariableTypes.INT, VariableTypes.DOUBLE, VariableTypes.LONG]
    semantic_information: SemanticInformation

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)

    def reset(self):
        if self.semantic_information.use_initial_value:
            self.value = self.semantic_information.initial_value
            self.has_current_value = True
        else:
            self.has_current_value = False
        self.has_been_written_to = False

    def __init__(self, name, variable_type, pos_x, pos_y, height, width, min_value, max_value,
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
                self.min_value = QDateTime.fromString(min_value, "yyyy-MM-ddThh:mm:ss")\
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
                self.max_value = QDateTime.fromString(max_value, "yyyy-MM-ddThh:mm:ss")\
                    .toSecsSinceEpoch()
            else:
                self.max_value = max_value
        else:
            self.max_value = None

        self.replacement = replacement
        self.has_been_written_to = False
