from src.jilg.Other.Global import print_summary_global

'''
This class is used to represent the generated event log.
'''


class EventLog:
    name: str
    creator: str
    traces: list

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)

    def __init__(self, name, creator):
        self.name = name
        self.creator = creator
        self.traces = []
