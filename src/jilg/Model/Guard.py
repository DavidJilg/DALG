from src.jilg.Other.Global import print_summary_global


class Guard:
    name: str
    guard_string: str

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)

    def __init__(self, name, guard_string, transition):
        self.name = name
        self.guard_string = guard_string
        self.transition = transition
