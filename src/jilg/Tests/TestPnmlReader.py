from unittest import TestCase

from src.jilg.Other.Global import VariableTypes
from src.jilg.Main.PnmlReader import PnmlReader
from src.jilg.Other.Global import test_files_path


class TestPnmlReader(TestCase):
    model1_path = test_files_path + "test_dpn.pnml"
    model1_name = "my dpn"
    model1_id = "net1"
    model1_type = "http://www.pnml.org/version-2009/grammar/pnmlcoremodel"

    model1_nr_of_places = 4
    model1_nr_of_transitions = 3
    model1_nr_of_arcs = 6
    model1_nr_of_final_markings = 2
    model1_nr_of_variables = 2

    model1_place1_id = "n1"
    model1_place1_name = "wait"
    model1_place1_pos_x = 11.25
    model1_place1_pos_y = 11.25
    model1_place1_dim_x = 12.5
    model1_place1_dim_y = 12.5
    model1_place1_token_count = 1
    model1_place1_fill_color = None
    model1_place1_inputs = []
    model1_place1_outputs = ["n5"]

    model1_transition_n5_guard = None
    model1_transition_n5_id = "n5"
    model1_transition_n5_name = "diagnose"
    model1_transition_n5_pos_x = 17.5
    model1_transition_n5_pos_y = 15.0
    model1_transition_n5_dim_x = 25.0
    model1_transition_n5_dim_y = 20.0
    model1_transition_n5_fill_color = "#FFFFFF"
    model1_transition_n5_inputs = ["n1"]
    model1_transition_n5_outputs = ["n2"]
    model1_transition_n5_read_variables = ["patient_status"]
    model1_transition_n5_write_variables = ["patient_status"]

    model1_transition_n6_id = "n6"
    model1_transition_n6_guard = "(patient_status==\"emergency\")"

    model1_arc_n8_id = "arc8"
    model1_arc_n8_source = "n5"
    model1_arc_n8_target = "n2"
    model1_arc_n8_name = "1"
    model1_arc_n8_type = "normal"

    model1_initial_marking = [('n1', 1), ('n2', 0), ('n3', 0), ('n4', 0)]
    model1_final_marking1 = [('n1', 0), ('n2', 0), ('n3', 0), ('n4', 1)]
    model1_final_marking2 = [('n1', 0), ('n2', 0), ('n3', 1), ('n4', 0)]

    model1_variable1_type = VariableTypes.STRING
    model1_variable1_value = ""
    model1_variable1_name = "patient_status"
    model1_variable1_pos_x = 0
    model1_variable1_pos_y = 0
    model1_variable1_height = 50
    model1_variable1_width = 50
    model1_variable1_min = None
    model1_variable1_max = None

    model1_variable2_min = 1.0
    model1_variable2_max = 100.0

    model2_path = test_files_path + "test_dpn2.pnml"

    reader: PnmlReader

    def setUp(self):
        self.reader = PnmlReader()

    def test_read_pnml(self):
        self.setUp()
        dpn = self.reader.read_pnml(self.model1_path)[0]
        self.check_model_conformance(dpn)

    def check_model_conformance(self, model):
        self.check_attributes(model)
        self.check_places(model)
        self.check_transitions(model)
        self.check_arcs(model)
        self.check_markings(model)
        self.check_variables(model)

    def check_attributes(self, model):
        self.assertEqual(self.model1_name, model.name)
        self.assertEqual(self.model1_id, model.id)
        self.assertEqual(self.model1_type, model.type)

    def check_places(self, model):
        self.assertEqual(len(model.places), self.model1_nr_of_places)
        place = model.get_place_or_transition_by_id(self.model1_place1_id)
        self.assertEqual(self.model1_place1_id, place.id)
        self.assertEqual(self.model1_place1_name, place.name)
        self.assertEqual(self.model1_place1_pos_x, place.pos_x)
        self.assertEqual(self.model1_place1_pos_y, place.pos_y)
        self.assertEqual(self.model1_place1_dim_x, place.dim_x)
        self.assertEqual(self.model1_place1_dim_y, place.dim_y)
        self.assertEqual(self.model1_place1_token_count, place.token_count)
        self.assertEqual(self.model1_place1_fill_color, place.fill_color)
        self.assertEqual(self.model1_place1_inputs, place.get_input_transition_ids())
        self.assertEqual(self.model1_place1_outputs, place.get_output_transition_ids())

    def check_transitions(self, model):
        self.assertEqual(self.model1_nr_of_transitions, len(model.transitions))
        transition = model.get_place_or_transition_by_id(self.model1_transition_n5_id)
        self.assertEqual(self.model1_transition_n5_id, transition.id)
        self.assertEqual(self.model1_transition_n5_name, transition.name)
        self.assertEqual(self.model1_transition_n5_pos_x, transition.pos_x)
        self.assertEqual(self.model1_transition_n5_pos_y, transition.pos_y)
        self.assertEqual(self.model1_transition_n5_dim_x, transition.dim_x)
        self.assertEqual(self.model1_transition_n5_dim_y, transition.dim_y)
        self.assertEqual(self.model1_transition_n5_fill_color, transition.fill_color)
        self.assertEqual(self.model1_transition_n5_inputs, transition.get_input_places_ids())
        self.assertEqual(self.model1_transition_n5_outputs, transition.get_output_places_ids())
        self.assertEqual(self.model1_transition_n5_guard, transition.guard)
        self.assertEqual(self.model1_transition_n5_read_variables, transition.get_reads_variables_ids())
        self.assertEqual(self.model1_transition_n5_write_variables, transition.get_writes_variables_names())

        transitionN6 = model.get_place_or_transition_by_id("n6")
        self.assertEqual(["patient_status"], transitionN6.get_reads_variables_ids())

        transition = model.get_place_or_transition_by_id(self.model1_transition_n6_id)
        self.assertEqual(self.model1_transition_n6_guard, transition.guard.guard_string)

    def check_arcs(self, model):
        self.assertEqual(self.model1_nr_of_arcs, len(model.arcs))

        arc = model.get_arc_by_id(self.model1_arc_n8_id)
        self.assertEqual(self.model1_arc_n8_id, arc.id)
        self.assertEqual(self.model1_arc_n8_source, arc.source)
        self.assertEqual(self.model1_arc_n8_target, arc.target)
        self.assertEqual(self.model1_arc_n8_name, arc.name)
        self.assertEqual(self.model1_arc_n8_type, arc.type)

    def check_markings(self, model):
        self.assertEqual(self.model1_final_marking1, model.final_markings[0].token_places)
        self.assertEqual(self.model1_final_marking2, model.final_markings[1].token_places)
        self.assertEqual(self.model1_initial_marking, model.current_marking.token_places)

    def check_variables(self, model):
        self.assertEqual(self.model1_nr_of_variables, len(model.variables))
        var = model.variables[0]

        self.assertEqual(self.model1_variable1_type, var.type)
        self.assertEqual(False, var.has_current_value)
        self.assertEqual(False, var.has_initial_value)
        self.assertEqual(self.model1_variable1_name, var.name)
        self.assertEqual(self.model1_variable1_pos_x, var.pos_x)
        self.assertEqual(self.model1_variable1_pos_y, var.pos_y)
        self.assertEqual(self.model1_variable1_height, var.height)
        self.assertEqual(self.model1_variable1_width, var.width)
        self.assertEqual(None, var.max_value)
        self.assertEqual(None, var.min_value)

        var = model.variables[1]
        self.assertEqual(float(self.model1_variable2_max), float(var.max_value))
        self.assertEqual(float(self.model1_variable2_min), float(var.min_value))
