from copy import deepcopy
from typing import Union

from src.jilg.Model.Arc import Arc
from src.jilg.Model.Marking import Marking
from src.jilg.Model.Place import Place
from src.jilg.Model.Transition import Transition
from src.jilg.Model.Variable import Variable
from src.jilg.Other.Global import print_summary_global
from src.jilg.Simulation.ValueGenerator import ValueGenerator

'''
This class is used to represent the model that is currently loaded. The PnmlReader will create an
instance of this class and of all subcomponents, e.g. places, transitions, when a model file is
loaded.
'''


class Model:
    name: str
    id: str
    type: str
    places: list
    transitions: list
    variables: list
    arcs: list
    initial_marking: Marking
    current_marking: Union[Marking, None]
    final_markings: list

    def __init__(self, name: str):
        self.name = name
        self.id = ""
        self.type = ""
        self.places = []
        self.transitions = []
        self.variables = []
        self.arcs = []
        self.current_marking = None
        self.final_markings = []

    def reset(self):
        self.current_marking = deepcopy(self.initial_marking)
        for variable in self.variables:
            variable.reset()
        for token_placement in self.current_marking.token_places:
            self.get_place_or_transition_by_id(token_placement[0]).token_count = token_placement[1]

    def reset_prime_variable_values(self):
        for variable in self.variables:
            variable.has_nex_value = False
            variable.next_value = []

    def generate_initial_values(self, gen: ValueGenerator):
        for variable in self.variables:
            variable.has_current_value = False
            variable.value = None
            variable.has_been_written_to = False
            if variable.semantic_information.use_initial_value:
                if variable.semantic_information.generate_initial_value:
                    variable.value = gen.generate_variable_value(variable, None)
                    variable.has_current_value = True
                    variable.has_been_written_to = True
                else:
                    variable.value = variable.semantic_information.initial_value
                    variable.has_current_value = True
                    variable.has_been_written_to = True

    def print_summary(self, print_list_elements: bool = False):
        print_summary_global(self, print_list_elements)

    def get_variable_by_name(self, var_name: str) -> Union[Variable, None]:
        for var in self.variables:
            if var.name == var_name or var.original_name == var_name:
                return var
        return None

    def get_arc_by_id(self, arc_id: str) -> Union[Arc, None]:
        for arc in self.arcs:
            if arc.id == arc_id:
                return arc
        return None

    def is_in_final_state(self) -> bool:
        for marking in self.final_markings:
            if self.check_final_marking(marking):
                return True
        return False

    def check_final_marking(self, final_marking: Marking) -> bool:
        for token_place in final_marking.token_places:
            if self.get_place_or_transition_by_id(token_place[0]).token_count != token_place[1]:
                return False
        return True

    def get_place_or_transition_by_id(self, object_id: str) -> Union[Place, Transition, None]:
        for transition in self.transitions:
            if transition.id == object_id:
                return transition
        for place in self.places:
            if place.id == object_id:
                return place
        return None

    def get_place_or_transition_by_name(self, name: str) -> Union[Place, Transition, None]:
        for transition in self.transitions:
            if transition.name == name:
                return transition
        for place in self.places:
            if place.name == name:
                return place
        return None

    def get_enabled_transitions(self, with_probabilities: bool, with_data: bool, value_gen: ValueGenerator) ->\
            ([Transition], Union[None, list[float]]):
        enabled_transitions = []
        for transition in self.transitions:
            if transition.is_enabled(with_data, value_gen):
                enabled_transitions.append(transition)

        if with_probabilities and enabled_transitions:
            probabilities = self.calculate_probabilities(enabled_transitions)
            return enabled_transitions, probabilities
        elif with_probabilities:
            return enabled_transitions, []
        else:
            return enabled_transitions

    def calculate_probabilities(self, enabled_transitions: [Transition]) -> [float]:
        weights = []
        for transition in enabled_transitions:
            weights.append(transition.config.weight)
        if sum(weights) == 0:
            new_weights = []
            for weight in weights:
                new_weights.append(1)
            weights = new_weights
        factor = (1 / sum(weights))
        probabilities = []
        for weight in weights:
            probabilities.append(weight * factor)

        # accounting for floating point error, probabilities must sum up to 1 for numpy.choice
        probabilities_sum = sum(probabilities)
        if probabilities_sum > 1:
            probabilities[-1] -= probabilities_sum - 1
        elif probabilities_sum < 1:
            probabilities[-1] += 1 - probabilities_sum
        return probabilities

    def fire_transition(self, transition_id: str, with_data: bool = True):
        transition = self.get_place_or_transition_by_id(transition_id)
        self.update_current_marking(transition.fire())

    def update_current_marking(self, effected_ids: [str]):
        new_token_places = []
        effected_input_places, effected_output_places = effected_ids
        for token_place in self.current_marking.token_places:
            if token_place[0] in effected_input_places and token_place[0] in effected_output_places:
                new_token_places.append(token_place)
            elif token_place[0] in effected_input_places:
                new_token_places.append((token_place[0], token_place[1] - 1))
            elif token_place[0] in effected_output_places:
                new_token_places.append((token_place[0], token_place[1] + 1))
            else:
                new_token_places.append(token_place)
        self.current_marking.token_places = new_token_places

    def setup_current_marking(self):
        new_token_places = []
        for place in self.places:
            new_token_places.append((place.id, place.token_count))
        self.current_marking.token_places = new_token_places
