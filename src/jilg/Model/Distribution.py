import numpy as np
import numpy.random
from scipy import stats
from scipy.stats import truncnorm

from src.jilg.Other.Global import print_summary_global

'''
This class is used to generate random numeric values that follow a distribution that was specified
by the user.
'''


class Distribution:
    mean: float
    standard_deviation: float
    minimum: float
    maximum: float
    has_mean: bool
    has_standard_deviation: bool
    has_maximum: bool
    has_minimum: bool
    distribution_type: str
    generator: None
    set_new_seed: bool
    rng: np.random.default_rng

    def print_summary(self, print_list_elements=False):
        print_summary_global(self, print_list_elements)

    def __init__(self, rng, distribution_type, other_arguments):
        if other_arguments["minimum"] == other_arguments["maximum"]:
            other_arguments["maximum"] += 1
        self.distribution_type = distribution_type
        self.set_new_seed = True
        self.rng = rng
        if 'mean' not in other_arguments:
            other_arguments["mean"] = (other_arguments["maximum"] -
                                       other_arguments["minimum"]) / 2
        if 'standard_deviation' not in other_arguments:
            other_arguments["standard_deviation"] = other_arguments["mean"] / 2

        self.mean = other_arguments["mean"]
        self.minimum = other_arguments["minimum"]
        self.maximum = other_arguments["maximum"]
        self.standard_deviation = other_arguments["standard_deviation"]
        if distribution_type == "truncated_normal" or distribution_type == "normal":
            self.generator = self.get_truncated_normal(other_arguments["mean"],
                                                       other_arguments["standard_deviation"],
                                                       other_arguments["minimum"],
                                                       other_arguments["maximum"])
            self.mean = other_arguments["mean"]
            self.has_mean = True
            self.standard_deviation = other_arguments["standard_deviation"]
            self.has_standard_deviation = True
            self.minimum = other_arguments["minimum"]
            self.has_minimum = True
            self.maximum = other_arguments["maximum"]
            self.has_maximum = True
        elif distribution_type == "uniform":
            self.minimum = other_arguments["minimum"]
            self.has_minimum = True
            self.maximum = other_arguments["maximum"]
            self.has_maximum = True
            self.has_mean = False
            self.has_standard_deviation = False
        elif distribution_type == "truncated_exponential" or distribution_type == "exponential":
            self.minimum = other_arguments["minimum"]
            self.maximum = other_arguments["maximum"]
            self.has_minimum = True
            self.has_maximum = True
            self.has_mean = True
            self.has_standard_deviation = True
            if self.mean == 0:
                self.mean = 0.0000000000000001
            self.generator = stats.truncexpon(
                b=(self.maximum - self.minimum) / self.standard_deviation,
                loc=self.minimum,
                scale=self.standard_deviation)

    def get_truncated_normal(self, mean, sd, low, upper):
        return truncnorm((low - mean) / sd, (upper - mean) / sd, loc=mean, scale=sd)

    def get_truncated_exponential(self, mean, sd, low, upper):
        return truncnorm((low - mean) / sd, (upper - mean) / sd, loc=mean, scale=sd)

    def get_next_int(self):
        return int(self.get_next_value())

    def get_next_float(self):
        return self.get_next_value()

    def get_next_value(self):
        if self.set_new_seed:
            numpy.random.seed(int(self.rng.uniform(0, 1000)))
            self.set_new_seed = False
        if self.distribution_type == "truncated_normal" or self.distribution_type == "normal":
            return self.generator.rvs()
        elif self.distribution_type == "uniform":
            return self.rng.uniform(self.minimum, self.maximum)
        elif self.distribution_type == "exponential" or \
                self.distribution_type == "truncated_exponential":
            return self.generator.rvs()
