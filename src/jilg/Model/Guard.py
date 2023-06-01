from src.jilg.Other.Global import print_summary_global

'''
An instance of this class is used for every guard in the internal model representation. 
'''


class Guard:
    name: str
    guard_string: str

    def print_summary(self, print_list_elements: bool = False):
        print_summary_global(self, print_list_elements)

    def __init__(self, name: str, guard_string: str, transition):
        self.name = name
        self.guard_string = guard_string
        self.transition = transition
