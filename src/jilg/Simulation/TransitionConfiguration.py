from src.jilg.Other import Global

'''
This class is used to store all semantic information regarding the firing of transitions.
'''


class TransitionConfiguration:
    transition_id: str
    activity_name: str
    weight: float

    use_general_config: bool

    avg_time_delay: int
    time_delay_sd: int
    time_delay_min: int
    time_delay_max: int

    avg_lead_time: int
    lead_time_sd: int
    lead_time_min: int
    lead_time_max: int

    no_time_forward: bool

    invisible: bool

    included_vars: list

    time_intervals: list
    add_time_interval_variance: bool
    max_time_interval_variance: int

    def print_summary(self, print_list_elements=False):
        Global.print_summary_global(self, print_list_elements)

    def __init__(self, transition_id):
        self.transition_id = transition_id
        self.activity_name = str(transition_id)
        self.weight = 1
        self.use_general_config = True
        self.invisible = False

        self.no_time_forward = False

        self.avg_time_delay = 0
        self.time_delay_sd = 1
        self.time_delay_min = 0
        self.time_delay_max = 1

        self.avg_lead_time = 0
        self.lead_time_sd = 1
        self.lead_time_min = 0
        self.lead_time_max = 1

        self.included_vars = []

        self.time_intervals = []
        self.add_time_interval_variance = False
        self.max_time_interval_variance = 0
