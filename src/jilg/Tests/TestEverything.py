from unittest import TestCase

from src.jilg.Tests.TestConfiguration import TestConfiguration
from src.jilg.Tests.TestMilpSolver import TestMilpSolver
from src.jilg.Tests.TestModel import TestModel
from src.jilg.Tests.TestModelAnalyser import TestModelAnalyser
from src.jilg.Tests.TestPnmlReader import TestPnmlReader

from src.jilg.Tests.TestSimulation import TestSimulation


class TestEverything(TestCase):

    def setUp(self):
        self.pnml_reader_test = TestPnmlReader()
        self.model_test = TestModel()
        self.logic_compiler_test = TestMilpSolver()
        self.configuration_test = TestConfiguration()
        self.model_analyser_test = TestModelAnalyser()
        self.simulation_test = TestSimulation()

    def test_everything(self):
        self.pnml_reader_test.test_read_pnml()
        self.model_test.test_model()
        self.logic_compiler_test.test_logic_compiler()
        self.configuration_test.test_all()
        self.model_analyser_test.test_all()
        self.simulation_test.test_all()
