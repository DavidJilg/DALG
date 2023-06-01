from typing import Union
from xml.etree.ElementTree import Element

from src.jilg.Model.Guard import Guard
from src.jilg.Model.Place import Place
from src.jilg.Other.Global import print_summary_global
from src.jilg.Simulation.TransitionConfiguration import TransitionConfiguration
from src.jilg.Model.MilpSolver import MilpSolver
from src.jilg.Simulation.ValueGenerator import ValueGenerator

'''
This class is used to represent all transitions of the internal model representation.
'''


class Transition:
    name: str
    id: str

    # Currently unused information that is often present in PNML files.
    pos_x: float
    pos_y: float
    dim_x: float
    dim_y: float
    tool_specific_info: Element
    fill_color: str
    # ---------------------------

    guard: Union[Guard, None]
    inputs: list
    outputs: list
    writes_variables: list
    reads_variables: list
    invisible: bool
    config: TransitionConfiguration
    milp_solver: MilpSolver
    value_gen: ValueGenerator

    def print_summary(self, print_list_elements: bool = False):
        print_summary_global(self, print_list_elements)

    def __init__(self, name: str):
        self.name = name
        self.id = ""
        self.invisible = False
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.dim_x = 0.0
        self.dim_y = 0.0
        self.tool_specific_info = None
        self.fill_color = ""
        self.guard = None
        self.inputs = []
        self.outputs = []
        self.model = None
        self.writes_variables = []
        self.reads_variables = []
        self.milp_solver = MilpSolver()

    def get_writes_variables_names(self) -> [str]:
        variable_names = []
        for var in self.writes_variables:
            variable_names.append(var.name)
        return variable_names

    def get_reads_variables_ids(self) -> [str]:
        variable_ids = []
        for var in self.reads_variables:
            variable_ids.append(var.name)
        return variable_ids

    def get_input_places_ids(self) -> [str]:
        place_ids = []
        for place in self.inputs:
            place_ids.append(place.id)
        return place_ids

    def get_output_places_ids(self) -> [str]:
        place_ids = []
        for place in self.outputs:
            place_ids.append(place.id)
        return place_ids

    def is_enabled(self, with_data: bool, value_gen: bool = None) -> bool:
        for input_place in self.inputs:
            tokens_needed = self.count_tokens_needed(input_place)
            if input_place.token_count < tokens_needed:
                return False
        if with_data:
            return self.evalute_guard(value_gen)
        else:
            return True

    def count_tokens_needed(self, input_place: Place) -> int:
        tokens_needed = 0
        for place in self.inputs:
            if place.id == input_place.id:
                tokens_needed += 1
        return tokens_needed

    def fire(self) -> ([Place], [Place]):
        effected_input_places = []
        effected_output_places = []
        for input_place in self.inputs:
            effected_input_places.append(input_place.id)
            input_place.token_count -= 1
        for output_place in self.outputs:
            effected_output_places.append(output_place.id)
            output_place.token_count += 1
        return effected_input_places, effected_output_places

    def evalute_guard(self, value_gen: ValueGenerator) -> bool:
        if self.guard is not None:
            return self.milp_solver.compile_and_evaluate_string(self.guard.guard_string,
                                                                self.reads_variables, self,
                                                                value_gen)
        else:
            return True
