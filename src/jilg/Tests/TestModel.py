from copy import deepcopy
from unittest import TestCase
from src.jilg.Main.PnmlReader import PnmlReader


class TestModel(TestCase):
    test_files_path = "../../../test_files/"
    model_path = test_files_path + "test_dpn.pnml"
    reader: PnmlReader
    model_step1_enabled_transitions = ["n5"]
    model_fire1 = "n5"
    model_fire2 = "n6"
    model_fire3 = "n7"
    model_step2_enabled_transitions = ["n7"]
    variable_name = "patient_status"
    arc_id = "arc8"
    place_id = "n1"
    transition_id = "n5"

    def setUp(self):
        self.reader = PnmlReader()

    def test_model(self):
        self.setUp()
        model = self.reader.read_pnml(self.model_path)[0]
        self.assertFalse(model.is_in_final_state())
        self.assertEqual(self.model_step1_enabled_transitions, self.get_transition_ids(model))
        model.fire_transition(self.model_fire1)
        self.assertFalse(model.is_in_final_state())
        self.assertEqual(self.model_step2_enabled_transitions, self.get_transition_ids(model))
        model2 = deepcopy(model)
        model.get_variable_by_name("patient_status").value = "emergency"
        model.get_variable_by_name("patient_status").has_current_value = True
        self.assertEqual(["n6"], self.get_transition_ids(model))
        model.fire_transition(self.model_fire2)
        self.assertTrue(model.is_in_final_state())
        self.assertEqual([], self.get_transition_ids(model))
        model2.fire_transition(self.model_fire3)
        self.assertTrue(model2.is_in_final_state())
        self.assertEqual([], self.get_transition_ids(model))

        self.assertTrue(model.get_variable_by_name(self.variable_name) is not None)
        self.assertTrue(model.get_variable_by_name(self.variable_name).name == self.variable_name)

        self.assertTrue(model.get_arc_by_id(self.arc_id) is not None)
        self.assertTrue(model.get_arc_by_id(self.arc_id).id == self.arc_id)

        self.assertTrue(model.get_place_or_transition_by_id(self.place_id) is not None)
        self.assertTrue(model.get_place_or_transition_by_id(self.place_id).id == self.place_id)

        self.assertTrue(model.get_place_or_transition_by_id(self.transition_id) is not None)
        self.assertTrue(model.get_place_or_transition_by_id(self.transition_id).id == self.transition_id)

    def get_transition_ids(self, model):
        transitions = model.get_enabled_transitions(False, True)
        ids = []
        for transition in transitions:
            ids.append(transition.id)
        return ids
