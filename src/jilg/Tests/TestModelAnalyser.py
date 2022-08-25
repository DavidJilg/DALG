from unittest import TestCase

import numpy as np

from src.jilg.Main.Configuration import Configuration
from src.jilg.Main.ModelAnalyser import ModelAnalyser
from src.jilg.Main.PnmlReader import PnmlReader
from src.jilg.Other.Global import VariableTypes
from src.jilg.Other import Global


class TestModelAnalyser(TestCase):
    analyser: ModelAnalyser
    value_tests = []
    value_tests.append(("variable1", "variable1 == 'value1'", (["value1"], True)))

    value_tests.append(("cancer_type",
                        "('maligne Melanom'==cancer_type) || (cancer_type == 'leukemia')",
                        (["maligne Melanom", "leukemia"], True)
                        ))

    value_tests.append(("cancer_type",
                        "('maligne Melanom'==cancer_type) || (cancer_type ==)",
                        (["maligne Melanom"], True)
                        ))

    value_tests.append(("cancer_type",
                        "('maligne Melanom'==cancer_type) || (  ==cancer_type)",
                        (["maligne Melanom"], True)
                        ))

    def setUp(self):
        self.analyser = ModelAnalyser()
        self.reader = PnmlReader()
        self.model = self.reader.read_pnml(Global.test_files_path + "test_dpn.pnml")[0]
        self.config = Configuration(np.random.default_rng(1701))
        self.config.create_basic_configuration(self.model, Global.test_files_path + "test_dpn.pnml")

    def test_all(self):
        self.setUp()
        self.test_check_for_values()
        self.test_with_model()
        self.test_with_model_with_int_variable()
        self.test_with_model_with_bool_variable()

    def test_check_for_values(self):
        for value_test in self.value_tests:
            self.assertEqual(value_test[2], self.analyser.check_for_values(value_test[1],
                                                                           value_test[0]))

    def test_with_model(self):
        self.analyser.analyse_model(self.model, self.config)
        var_values = self.model.get_variable_by_name("patient_status").semantic_information.values
        config_values = self.config.get_sem_info_by_variable_name("patient_status").values
        self.assertEqual([['emergency'], [1]], var_values)
        self.assertEqual([['emergency'], [1]], config_values)

    def test_with_model_with_int_variable(self):
        self.model = self.reader.read_pnml(Global.test_files_path + "test_dpn.pnml")[0]
        self.config = Configuration(np.random.default_rng(1701))
        extended_guard = "((variable2 / 5) == 0.6) && variable2 == 5 || variable2 == 10 "
        self.model.get_place_or_transition_by_id("n6").guard.guard_string = extended_guard

        self.config.create_basic_configuration(self.model, Global.test_files_path + "test_dpn.pnml")
        self.analyser.analyse_model(self.model, self.config)
        var_values = self.model.get_variable_by_name("variable2").semantic_information.values
        config_values = self.config.get_sem_info_by_variable_name("variable2").values
        self.assertEqual([[5, 10], [1, 1]], var_values)
        self.assertEqual([[5, 10], [1, 1]], config_values)

    def test_with_model_with_bool_variable(self):
        self.model = self.reader.read_pnml(Global.test_files_path + "test_dpn.pnml")[0]
        self.config = Configuration(np.random.default_rng(1701))
        extended_guard = "((variable2 / 5) == 0.6) && variable2 == false || variable2 == true"
        self.model.get_variable_by_name("variable2").type = VariableTypes.BOOL
        self.model.get_place_or_transition_by_id("n6").guard.guard_string = extended_guard

        self.config.create_basic_configuration(self.model,
                                               Global.test_files_path + "test_dpn.pnml")
        self.analyser.analyse_model(self.model, self.config)
        var_values = self.model.get_variable_by_name("variable2").semantic_information.values
        config_values = self.config.get_sem_info_by_variable_name("variable2").values
        self.assertEqual([[False, True], [1, 1]], var_values)
        self.assertEqual([[False, True], [1, 1]], config_values)