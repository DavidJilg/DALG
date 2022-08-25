from xml.etree.ElementTree import Element

from src.jilg.Model.Model import Model
from src.jilg.Other.Global import print_summary_global


class Place:
    name: str
    id: str
    model: Model
    token_count: int
    pos_x: float
    pos_y: float
    dim_x: float
    dim_y: float
    fill_color: str
    tool_specific_info: Element
    inputs: []
    outputs: []

    def __init__(self, name):
        self.name = name
        self.id = ""
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.dim_x = 0.0
        self.dim_y = 0.0
        self.fill_color = None
        self.tool_specific_info = None
        self.inputs = []
        self.outputs = []
        self.model = None
        self.token_count = 0

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)

    def get_input_transition_ids(self):
        transitions = []
        for transition in self.inputs:
            transitions.append(transition.id)
        return transitions

    def get_output_transition_ids(self):
        transitions = []
        for transition in self.outputs:
            transitions.append(transition.id)
        return transitions
