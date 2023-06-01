from typing import Union
from xml.etree.ElementTree import Element

from src.jilg.Other.Global import print_summary_global

'''
This class is used to represent all places of the internal model representation.
'''


class Place:
    name: str
    id: str
    token_count: int
    pos_x: float
    pos_y: float
    dim_x: float
    dim_y: float
    fill_color: Union[None, str]
    tool_specific_info: Union[None, Element]
    inputs: []
    outputs: []
    final_marking_token_count: Union[None, int]

    def __init__(self, name: str):
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
        self.final_marking_token_count = None

    def print_summary(self, print_list_elements: bool = False):
        print_summary_global(self, print_list_elements)

    def get_input_transition_ids(self) -> [str]:
        transition_ids = []
        for transition in self.inputs:
            transition_ids.append(transition.id)
        return transition_ids

    def get_output_transition_ids(self) -> [str]:
        transition_ids = []
        for transition in self.outputs:
            transition_ids.append(transition.id)
        return transition_ids
