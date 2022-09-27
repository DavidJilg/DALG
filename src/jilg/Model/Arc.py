from xml.etree.ElementTree import Element

from src.jilg.Other.Global import print_summary_global

'''
An instance of this class is used for every arc in the internal model representation. 
'''


class Arc:
    name: str
    id: str
    source: str
    target: str
    type: str
    tool_specific_info: Element

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)

    def __init__(self, name, arc_id, source, target, arc_type, tool_specific_info, model):
        self.name = name
        self.id = arc_id
        self.source = source
        self.target = target
        self.type = arc_type
        self.tool_specific_info = tool_specific_info
