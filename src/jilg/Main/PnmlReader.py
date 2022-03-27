import traceback
import xml.etree.ElementTree as Et
from copy import deepcopy

from src.jilg.Model.Arc import Arc
from src.jilg.Model.Guard import Guard
from src.jilg.Model.Marking import Marking
from src.jilg.Model.MilpSolver import Operators
from src.jilg.Model.Model import Model
from src.jilg.Model.Place import Place
from src.jilg.Model.Transition import Transition
from src.jilg.Model.Variable import Variable


class PnmlReader:
    undefined_id_count: int
    final_marking_missing: bool
    warning: bool
    warnings: list
    initial_marking_found: bool
    errors: list

    def __init__(self):
        self.undefined_id_count = 0
        self.final_marking_missing = False
        self.warning = False
        self.initial_marking_found = False
        self.warnings = []

    def read_pnml(self, path):
        try:
            model_obj, net = self.setup_model(path)
            self.read_variables(model_obj, net)
            self.read_pages(model_obj, net, self.get_children_by_tag(net, "page"))
            self.read_page(model_obj, net)
            self.read_final_markings(model_obj, net)
            self.configure_arc_references(model_obj)
            model_obj.setup_current_marking()
            model_obj.initial_marking = deepcopy(model_obj.current_marking)
            self.replace_non_valid_variable_names(model_obj)
            self.add_missing_read_variables(model_obj)
            self.check_model_conformance(model_obj)
            return model_obj, self.warnings
        except MissingEssentialValueError as error:
            print("The following error occurred while parsing the model: "+error.message)
            self.errors = [error.message]
            return None, self.errors
        except ModelConformanceError as error:
            print("The following error occurred while checking the conformance of the model: "
                  + error.message)
            self.errors = [error.message]
            return None, self.errors
        except FileNotFoundError:
            error_message = "File not found!"
            print("The following error occurred while checking the conformance of the model: "
                  + error_message)
            self.errors = [error_message]
            return None, self.errors
        except Exception as error:
            print(traceback.format_exc())
            self.errors = [str(type(error).__name__)]
            return None, self.errors

    def add_missing_places_in_final_markings(self, model_obj):
        place_ids = []
        for place in model_obj.places:
            place_ids.append(place.id)
        for final_marking in model_obj.final_markings:
            for place_id in place_ids:
                place_missing = True
                for token_placement in final_marking.token_places:
                    if token_placement[0] == place_id:
                        place_missing = False
                        break
                if place_missing:
                    final_marking.token_places.append((place_id, 0))


    def replace_non_valid_variable_names(self, model):
        replacement_index = 0
        var_names = []
        variables = []
        for variable in model.variables:
            var_names.append(variable.name)
            variables.append(variable)
        tmp = list(zip(var_names, variables))
        tmp.sort(key=lambda s: len(s[0]))
        tmp.reverse()
        while True:
            tmp.sort(key=lambda s: len(s[0]))
            tmp.reverse()
            var_names = []
            for var_tuple in tmp:
                var_names.append(var_tuple[0])
            var_needs_replacement = False
            var_replacement_name = ""

            for var_name in var_names:
                for var_name2 in var_names:
                    if var_name2 != var_name:
                        if var_name2 in var_name:
                            if not var_needs_replacement:
                                var_needs_replacement = True
                                var_replacement_name = var_name
                            break
                if var_needs_replacement:
                    break
            if not var_needs_replacement:
                break
            else:
                tmp_copy = []
                replacement_tuple = None
                for var_tuple in tmp:
                    if var_replacement_name == var_tuple[0]:
                        replacement_tuple = var_tuple
                    else:
                        tmp_copy.append(var_tuple)
                replacement_tuple = ("replacement_name"+str(replacement_index),
                                     replacement_tuple[1])
                replacement_tuple[1].original_name = replacement_tuple[1].name
                replacement_tuple[1].name = replacement_tuple[0]
                replacement_tuple[1].replacement = True
                tmp_copy.append(replacement_tuple)
                tmp = tmp_copy
                replacement_index += 1
        invalid_chars = [" '&',  '|',  '=',  '!',  '(', ')',  "]
        for operator in Operators:
            if operator != Operators.NONE:
                invalid_chars += "'{value}',  ".format(value=operator.value)
        invalid_chars = invalid_chars[:-3]
        for variable in model.variables:
            raise_error = False
            if variable.name == "&":
                raise_error = True
                operator = "&"
            elif variable.name == "|":
                raise_error = True
                operator = "|"
            elif variable.name == "=":
                raise_error = True
                operator = "="
            elif variable.name == "!":
                raise_error = True
                operator = "!"
            if raise_error:
                raise ModelConformanceError("Variable has a name equal to"
                                            " '{operator}' . Variable names are not allowed"
                                            " to be equal to the following values:"
                                            " {operator_values}"
                                            .format(operator=operator,
                                                    operator_values=invalid_chars))
        for variable in model.variables:
            for operator in Operators:
                if operator != Operators.NONE:
                    if variable.name == operator.value:
                        raise ModelConformanceError("Variable has a name equal to the operator"
                                                    " '{operator}' . Variable names are not allowed"
                                                    " to be equal to the following values:"
                                                    " {operator_values}"
                                                    .format(operator=operator.value,
                                                            operator_values=invalid_chars))
                    else:
                        if operator.value in variable.name:
                            variable.original_name = variable.name
                            variable.name = "replacement_variable"+str(replacement_index)
                            variable.replacement = True
                            replacement_index += 1

        invalid_chars = ['&', '|', '=', '!', '(', ')']
        for operator in Operators:
            if operator != Operators.NONE:
                invalid_chars.append(operator.value)
        for variable in model.variables:
            for char in invalid_chars:
                if char in variable.name:
                    variable.original_name = variable.name
                    variable.name = "replacement_variable" + str(replacement_index)
                    variable.replacement = True
                    replacement_index += 1

        var_names = []
        var_original_names = []
        variables = []
        for variable in model.variables:
            if variable.replacement:
                var_names.append(variable.name)
                var_original_names.append(variable.original_name)
                variables.append(variable)
        replacement_vars = list(zip(var_original_names, var_names, variables))
        replacement_vars.sort(key=lambda s: len(s[0]))
        replacement_vars.reverse()
        for trans in model.transitions:
            for var in replacement_vars:
                if trans.guard is not None:
                    if var[0] in trans.guard.guard_string:
                        trans.guard.guard_string = trans.guard.guard_string.replace(var[0], var[1])


    def check_model_conformance(self, model_obj):
        if len(model_obj.places) < 1:
            raise ModelConformanceError("The model has no places!")
        if len(model_obj.transitions) < 1:
            raise ModelConformanceError("The model has no transitions!")
        if len(model_obj.arcs) < 1:
            raise ModelConformanceError("The model has no arcs!")
        for place in model_obj.places:
            if len(place.inputs) + len(place.outputs) < 1:
                self.warnings.append("Place with the id '{id}' is not connected to any"
                                     " transitions!".format(id=place.id))
        for transition in model_obj.transitions:
            if len(transition.inputs) + len(transition.outputs) < 1:
                self.warnings.append("Transition with the id '{id}' is not connected to any"
                                     " places!".format(id=transition.id))
            if transition.guard is not None:
                if transition.guard.guard_string == "" or transition.guard.guard_string is None:
                    self.warnings.append("Transition with the id '{id}' has a invalid guard!"
                                         .format(id=transition.id))
        if len(model_obj.final_markings) < 1:
            self.warnings.append("The model has no final markings!")
        initial_token = False
        for token_place in model_obj.current_marking.token_places:
            if token_place[1] > 0:
                initial_token = True
                break
        if not initial_token:
            raise ModelConformanceError("No place has a token in the initial marking!")

    def add_missing_read_variables(self, model_obj):
        for transition in model_obj.transitions:
            if transition.guard is not None:
                guard_string = transition.guard.guard_string
                for variable in model_obj.variables:
                    if variable.name in guard_string:
                        ref_missing = True
                        for variable_ref in transition.reads_variables:
                            if variable_ref == variable:
                                ref_missing = False
                                break
                        if ref_missing:
                            transition.reads_variables.append(variable)

    def setup_model(self, path):
        tree = Et.parse(path)
        root = tree.getroot()
        net = root[0]
        name_element = self.get_child_by_tag(net, "name")
        if name_element is not None:
            name = name_element[0].text
        else:
            name = "no name defined"
        model_obj = Model(name)
        model_obj.id = net.attrib.get("id", None)
        model_obj.type = net.attrib.get("type", None)
        model_obj.current_marking = Marking("currentMarking")
        model_obj.final_markings = []
        return model_obj, net

    def read_final_markings(self, model_obj, net):
        final_marking_top = self.get_child_by_tag(net, "finalmarkings")
        if final_marking_top is not None:
            final_markings = self.get_children_by_tag(final_marking_top, "marking")
            if final_markings is not None:
                for index, final_marking in enumerate(final_markings):
                    self.add_final_marking(model_obj, final_marking, index)
            else:
                self.final_marking_missing = True
                self.warnings.append("No final marking/markings defined!")
        else:
            self.final_marking_missing = True
            self.warnings.append("No final marking/markings defined!")

    def configure_arc_references(self, model_obj):
        for arc in model_obj.arcs:
            source = model_obj.get_place_or_transition_by_id(arc.source)
            target = model_obj.get_place_or_transition_by_id(arc.target)
            source.outputs.append(target)
            target.inputs.append(source)

    def read_pages(self, model_obj, net, pages):
        if pages is not None:
            for page in pages:
                subpages = self.get_children_by_tag(page, "page")
                if subpages is not None:
                    self.read_pages(model_obj, net, subpages)
                self.read_page(model_obj, page)

    def read_page(self, model_obj, page):
        places = self.get_children_by_tag(page, "place")
        if places is not None:
            for place in places:
                self.add_place(model_obj, place)
        transitions = self.get_children_by_tag(page, "transition")
        if transitions is not None:
            for transition in transitions:
                self.add_transition(model_obj, transition)
        arcs = self.get_children_by_tag(page, "arc")
        if arcs is not None:
            for arc in arcs:
                self.add_arc(model_obj, arc)

    def add_place(self, model_obj, element):
        place = Place(self.get_element_name(element))
        place.id = element.attrib.get("id", None)
        if place.id is None or place.id == "":
            raise MissingEssentialValueError("Place defined with out an id!")
        place.model = Model
        place.tool_specific_info = element.attrib.get("toolspecific", None)
        self.add_graphics(place, element)
        initial_marking = self.get_child_by_tag(element, "initialMarking")
        initial_marking_warning = "Invalid initial marking definition for the place with the id" \
                                  " '{place_id}'!".format(place_id = place.id)
        if initial_marking is not None:
            if len(initial_marking) > 0:
                initial_marking_text = initial_marking[0].text
                if initial_marking_text is not None:
                    try:
                        place.token_count = int(initial_marking_text)
                        if int(initial_marking[0].text) > 0:
                            self.initial_marking_found = True
                        else:
                            place.token_count = 0
                            self.warnings.append(initial_marking_warning)
                    except TypeError:
                        self.warnings.append(initial_marking_warning)
                else:
                    self.warnings.append(initial_marking_warning)
            else:
                self.warnings.append(initial_marking_warning)
        model_obj.places.append(place)

    def add_transition_variables(self, model_obj, transition, element):
        variables_written = self.get_children_by_tag(element, "writeVariable")
        if not not variables_written:
            for variable in variables_written:
                variable_ref = model_obj.get_variable_by_name(variable.text)
                if variable_ref is not None:
                    transition.writes_variables.append(variable_ref)
                else:
                    self.warnings.append("Transition with the id '{id}' writes to variable that is"
                                         " not defined! Ignoring this write"
                                         " operation!".format(id=transition.id))
        variables_read = self.get_children_by_tag(element, "readVariable")
        if not not variables_read:
            for variable in variables_read:
                variable_ref = model_obj.get_variable_by_name(variable.text)
                if variable_ref is not None:
                    transition.reads_variables.append(variable_ref)
                else:
                    self.warnings.append("Transition with the id '{id}' reads variable that is"
                                         " not defined! Ignoring this read"
                                         " operation!".format(id=transition.id))

    def add_transition(self, model_obj, element):
        transition = Transition(self.get_element_name(element))
        transition.id = element.attrib.get("id", None)
        invisible = element.attrib.get("invisible", None)
        if type(invisible) == str:
            if invisible in ["false", "False", "FALSE"]:
                invisible = False
            else:
                invisible = True
        if invisible is not None:
            transition.invisible = invisible
        if transition.id is None:
            raise MissingEssentialValueError("Transition defined without and id!")
        self.add_transition_variables(model_obj, transition, element)
        guard = element.get("guard", None)
        if guard is not None:
            transition.guard = Guard("guard", guard, transition)
        transition.tool_specific_info = element.attrib.get("toolspecific", None)
        self.add_graphics(transition, element)
        model_obj.transitions.append(transition)

    def add_graphics(self, net_object, element):
        graphics = self.get_child_by_tag(element, "graphics")
        if graphics is not None:
            position = self.get_child_by_tag(graphics, "position")
            if position is not None:
                net_object.pos_x = float(position.get("x", None))
                net_object.pos_y = float(position.get("y", None))
            dimension = self.get_child_by_tag(graphics, "dimension")
            if dimension is not None:
                net_object.dim_x = float(dimension.get("x", None))
                net_object.dim_y = float(dimension.get("y", None))
            fill = self.get_child_by_tag(graphics, "fill")
            if fill is not None:
                net_object.fill_color = fill.get("color", None)

    def add_arc(self, model_obj, element):
        name = self.get_element_name(element)
        arc_id = element.get("id", None)
        source = element.get("source", None)
        target = element.get("target", None)
        if source is None or target is None:
            if source is None:
                self.warnings.append("Arc defined without source! Ignoring this arc!")
            if target is None:
                self.warnings.append("Arc defined without target! Ignoring this arc!")
        else:
            if model_obj.get_place_or_transition_by_id(source) is None:
                self.warnings.append("Arc defined without source! Ignoring this arc!")
            elif model_obj.get_place_or_transition_by_id(target) is None:
                self.warnings.append("Arc defined without target! Ignoring this arc!")
            else:
                tool_specific_info = self.get_child_by_tag(element, "toolspecific")
                arc_type_element = self.get_child_by_tag(element, "arctype")
                if arc_type_element is not None:
                    arc_type = arc_type_element[0].text
                else:
                    arc_type = "undefined"
                model_obj.arcs.append(Arc(name, arc_id, source, target, arc_type, tool_specific_info,
                                          model_obj))

    def add_final_marking(self, model_obj, element, marking_id):
        valid = True
        marking = Marking(str(marking_id))
        place_markings = self.get_children_by_tag(element, "place")
        if place_markings is not None:
            for place_marking in place_markings:
                place_id = place_marking.get("idref")
                if place_id is None or model_obj.get_place_or_transition_by_id(place_id) is None:
                    self.warnings.append("Invalid final marking definition found! Ignoring this"
                                         " definition!")
                    valid = False
                else:
                    try:
                        token_count = int(place_marking[0].text)
                        marking.token_places.append((place_id, token_count))
                    except TypeError:
                        valid = False
                        self.warnings.append("Invalid final marking definition found! Ignoring this"
                                             " definition!")
            if valid:
                model_obj.final_markings.append(marking)
        else:
            self.warnings.append("Invalid final marking definition found! Ignoring this"
                                 " definition!")

    def add_variable(self, variable, model_obj):
        var_min_value = variable.get("minValue", None)
        var_max_value = variable.get("maxValue", None)
        var_initial_value = variable.get("value", None)
        name_element = self.get_child_by_tag(variable, "name")
        if name_element is None or name_element.text is None:
            raise MissingEssentialValueError("Variable defined without name!")
        var_type = variable.get("type", None)
        var_name = name_element.text
        if var_type is None:
            var_type = "java.lang.String"
            self.warnings.append("Missing variable type for variable '{var_name}':"
                                 " assuming 'String' type!")
        try:
            var_pos_x = float(self.get_child_by_tag(variable, "position").get("x", 0))
            var_pos_y = float(self.get_child_by_tag(variable, "position").get("y", 0))
            var_height = float(self.get_child_by_tag(variable, "dimension").get("height", 50))
            var_width = float(self.get_child_by_tag(variable, "dimension").get("width", 50))
        except:
            var_pos_x = 0.0
            var_pos_y = 0.0
            var_height = 50
            var_width = 50
        model_obj.variables.append(Variable(var_name, var_type, var_pos_x, var_pos_y, var_height,
                                            var_width, var_min_value, var_max_value,
                                            var_initial_value))

    def get_element_name(self, element):
        name_element = self.get_child_by_tag(element, "name")
        if name_element is not None:
            return name_element[0].text
        else:
            self.undefined_id_count += 1
            return str(self.undefined_id_count)

    def read_variables(self, model_obj, net):
        variable_parent = self.get_child_by_tag(net, "variables")
        if variable_parent is not None:
            for variable in list(variable_parent):
                self.add_variable(variable, model_obj)

    def get_child_by_tag(self, parent_element, tag):
        for child in list(parent_element):
            if child.tag == tag:
                return child
        return None

    def get_children_by_tag(self, parent_element, tag):
        children = []
        for child in list(parent_element):
            if child.tag == tag:
                children.append(child)
        if not children:
            return None
        else:
            return children


class MissingEssentialValueError(Exception):

    def __init__(self, value, message="{value}"):
        self.value = value
        self.message = message.format(value=value)
        super().__init__(self.message)

class ModelConformanceError(Exception):

    def __init__(self, value, message="{value}"):
        self.value = value
        self.message = message.format(value=value)
        super().__init__(self.message)


