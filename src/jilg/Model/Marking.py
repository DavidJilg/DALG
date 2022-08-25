from src.jilg.Other.Global import print_summary_global


class Marking:
    name: str
    token_places: list

    def __init__(self, name):
        self.name = name
        self.token_places = []

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)

    def to_string(self, model=None):
        if model is None:
            string = self.name + ": "
            for index, token_place in enumerate(self.token_places):
                if index != 0:
                    string += ", "+str(token_place)
                else:
                    string += str(token_place)
            return string
        else:
            string = self.name + ": "
            for index, token_place in enumerate(self.token_places):
                name = model.get_place_or_transition_by_id(token_place[0]).name
                tokens = token_place[1]
                if tokens != 0:
                    if index != 0:
                        string += ", " + f"({name}, {tokens})"
                    else:
                        string += str(token_place)
            return string

    def to_minimalistic_string(self):
        string = self.name + ": "
        for index, token_place in enumerate(self.token_places):
            if token_place[1] > 0:
                if index != 0:
                    string += ", " + str(token_place)
                else:
                    string += str(token_place)
        return string
