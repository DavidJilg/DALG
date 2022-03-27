import xml.etree.ElementTree as ET
from copy import deepcopy
from xml.dom import minidom

import numpy as np


class XesWriter:
    def write_event_logs_to_xes_file(self, output_dir, event_logs, write_to_single_file,
                                     file_name, trace_names, include_invisible_transitions,
                                     include_metadata):
        if write_to_single_file:
            self.write_event_logs_to_single_file(output_dir, event_logs, include_metadata,
                                                 file_name, trace_names[0],
                                                 include_invisible_transitions)
        else:
            self.write_event_logs_to_separate_files(output_dir, event_logs,
                                                    include_invisible_transitions, include_metadata,
                                                    file_name,
                                                    trace_names[0])

    def write_event_logs_to_single_file(self, path, event_logs, include_invisible_transitions,
                                        include_metadata,
                                        file_name="event_log",
                                        trace_name="trace"):
        with open(path + file_name + ".xes", 'w') as file:
            for index, event_log in enumerate(event_logs):
                event_log_xml = self.generate_xml(event_log, trace_name,
                                                  include_invisible_transitions, include_metadata)
                if index != 0:
                    event_log_xml = event_log_xml.replace('<?xml version="1.0" ?>\n', '')
                if index != len(event_logs) - 1:
                    event_log_xml += "\n"
                file.write(event_log_xml)

    def write_event_logs_to_separate_files(self, path, event_logs, include_invisible_transitions,
                                           include_metadata,
                                           file_name="event_log",
                                           trace_name="trace"):
        if len(event_logs) == 1:
            event_log_xml = self.generate_xml(event_logs[0], trace_name,
                                              include_invisible_transitions, include_metadata)
            with open(path + file_name + ".xes", 'w') as file:
                file.write(event_log_xml)
        else:
            for index, event_log in enumerate(event_logs):
                event_log_xml = self.generate_xml(event_log, trace_name,
                                                  include_invisible_transitions, include_metadata)
                with open(path + file_name + str(index + 1) + ".xes", 'w') as file:
                    file.write(event_log_xml)

    def generate_xml(self, event_log, trace_name, include_invisible_transitions, include_metadata):
        tree = self.init_element_tree(event_log, include_invisible_transitions, include_metadata)
        name = ET.SubElement(tree.getroot(), "string")
        name.set("key", "concept:name")
        name.set("value", event_log.name)
        self.add_traces(tree.getroot(), event_log, trace_name, include_invisible_transitions)

        et_bytes = ET.tostring(tree.getroot())
        rough_xml = str(et_bytes)[2:-1].replace('\n', '')
        reparsed = minidom.parseString(rough_xml)
        pretty_xml = reparsed.toprettyxml(indent="  ").split("?>")[1][1:]
        xml_declaration = '<?xml version="1.0" ?>\n'
        comments = "<!-- This file has been generated with DALG:" \
                   " The Data Aware Event Log Generator -->\n" \
                   "<!-- https://github.com/DavidJilg/DALG -->\n"
        return xml_declaration + comments + pretty_xml

    def add_traces(self, root, event_log, trace_name, include_invisible_transitions):
        for index, trace in enumerate(event_log.traces):
            trace_element = ET.SubElement(root, "trace")
            name = ET.SubElement(trace_element, "string")
            name.set("key", "concept:name")
            if len(event_log.traces) == 1:
                if trace_name == "":
                    name.set("value", "1")
                else:
                    name.set("value", trace_name)
            else:
                name.set("value", trace_name + str(index+1))
            for variable in trace.variables:
                var = ET.SubElement(trace_element, variable[2])
                var.set("key", variable[0])
                var.set("value", str(variable[1]))
            for event in trace.events:
                self.add_event(trace_element, event, include_invisible_transitions)

    def add_event(self, trace_element, event, include_invisible_transitions):
        if not event.from_invisible_transition or include_invisible_transitions:
            event_element = ET.SubElement(trace_element, "event")
            name = ET.SubElement(event_element, "string")
            name.set("key", "concept:name")
            name.set("value", event.name)
            for variable in event.variables:
                var_name, var_value, var_type = variable
                var_element = ET.SubElement(event_element, var_type)
                var_element.set("key", var_name)
                var_element.set("value", str(var_value))

    def init_element_tree(self, event_log, include_invisible_transitions, include_metadata):
        root = ET.Element('log')
        root.set("xes.version", "1.0")
        root.set("xmlns", "http://www.xes-standard.org/")
        root.set("creator", "DALG")

        extension_concept = ET.SubElement(root, "extension")
        extension_concept.set("name", "Concept")
        extension_concept.set("prefix", "concept")
        extension_concept.set("uri", "http://www.xes-standard.org/concept.xesext")

        extension_time = ET.SubElement(root, "extension")
        extension_time.set("name", "Time")
        extension_time.set("prefix", "time")
        extension_time.set("uri", "http://www.xes-standard.org/time.xesext")

        if include_metadata:
            self.add_metadata(root, event_log, include_invisible_transitions)

        scope_event = ET.SubElement(root, "global")
        scope_event.set("scope", "trace")

        concept_name_trace = ET.SubElement(scope_event, "string")
        concept_name_trace.set("key", "concept:name")
        concept_name_trace.set("value", "DEFAULT")

        scope_event = ET.SubElement(root, "global")
        scope_event.set("scope", "event")

        concept_name = ET.SubElement(scope_event, "string")
        concept_name.set("key", "concept:name")
        concept_name.set("value", "DEFAULT")

        concept_time = ET.SubElement(scope_event, "date")
        concept_time.set("key", "time:timestamp")
        concept_time.set("value", "1970-01-01T01:00:00.000+01:00")

        return ET.ElementTree(root)

    def filter_invisible_transitions(self, log):
        new_log = deepcopy(log)
        for trace in new_log.traces:
            new_events = []
            for event in trace.events:
                if not event.from_invisible_transition:
                    new_events.append(event)
            trace.events = new_events
        return new_log

    def add_metadata(self, root, event_log_original, include_invisible_transitions):
        if include_invisible_transitions:
            event_log = event_log_original
        else:
            event_log = self.filter_invisible_transitions(event_log_original)
        extension_meta_general = ET.SubElement(root, "extension")
        extension_meta_general.set("name", "General metadata")
        extension_meta_general.set("prefix", "meta_general")
        extension_meta_general.set("uri", "http://www.xes-standard.org/meta_general.xesext")

        extension_meta_concept = ET.SubElement(root, "extension")
        extension_meta_concept.set("name", "Metadata Concept")
        extension_meta_concept.set("prefix", "meta_concept")
        extension_meta_concept.set("uri", "http://www.xes-standard.org/meta_concept.xesext")

        tmp = ET.SubElement(root, "int")
        tmp.set("key", "meta_general:traces_total")
        tmp.set("value", str(len(event_log.traces)))

        number_of_events = 0
        number_of_events_traces = []
        for trace in event_log.traces:
            number_of_events += len(trace.events)
            number_of_events_traces.append(len(trace.events))
        tmp = ET.SubElement(root, "int")
        tmp.set("key", "meta_general:events_total")
        tmp.set("value", str(number_of_events))

        avg_events = sum(number_of_events_traces)/len(number_of_events_traces)
        tmp = ET.SubElement(root, "float")
        tmp.set("key", "meta_general:events_average")
        tmp.set("value", str(avg_events))

        min_events = min(number_of_events_traces)
        max_events = max(number_of_events_traces)
        tmp = ET.SubElement(root, "int")
        tmp.set("key", "meta_general:events_min")
        tmp.set("value", str(min_events))

        tmp = ET.SubElement(root, "int")
        tmp.set("key", "meta_general:events_max")
        tmp.set("value", str(max_events))

        number_of_events_sd = np.std(number_of_events_traces)

        tmp = ET.SubElement(root, "float")
        tmp.set("key", "meta_general:events_standard_deviation")
        tmp.set("value", str(number_of_events_sd))

        # Conept General
        event_names = []
        event_names_traces = []
        for trace in event_log.traces:
            event_names_tmp = []
            for event in trace.events:
                event_names.append(event.name)
                event_names_tmp.append(event.name)

            event_names_traces.append(len(list(dict.fromkeys(event_names_tmp))))

        event_names = list(dict.fromkeys(event_names))
        number_of_names = len(event_names)
        tmp = ET.SubElement(root, "int")
        tmp.set("key", "meta_concept:different_names_total")
        tmp.set("value", str(number_of_names))

        avg_event_names = sum(event_names_traces)/len(event_names_traces)
        tmp = ET.SubElement(root, "float")
        tmp.set("key", "meta_concept:different_names_average")
        tmp.set("value", str(avg_event_names))

        event_names_sd = np.std(event_names_traces)
        tmp = ET.SubElement(root, "float")
        tmp.set("key", "meta_concept:different_names_standard_deviation")
        tmp.set("value", str(event_names_sd))

        event_names_min = min(event_names_traces)
        tmp = ET.SubElement(root, "int")
        tmp.set("key", "meta_concept:different_names_min")
        tmp.set("value", str(event_names_min))

        event_names_max = max(event_names_traces)
        tmp = ET.SubElement(root, "int")
        tmp.set("key", "meta_concept:different_names_max")
        tmp.set("value", str(event_names_max))

        tmp = ET.SubElement(root, "int")
        tmp.set("key", "meta_concept:named_events_total")
        tmp.set("value", str(number_of_events))

        tmp = ET.SubElement(root, "float")
        tmp.set("key", "meta_concept:named_events_average")
        tmp.set("value", str(avg_events))

        tmp = ET.SubElement(root, "float")
        tmp.set("key", "meta_concept:named_events_standard_deviation")
        tmp.set("value", str(number_of_events_sd))

        tmp = ET.SubElement(root, "int")
        tmp.set("key", "meta_concept:named_events_min")
        tmp.set("value", str(min_events))

        tmp = ET.SubElement(root, "int")
        tmp.set("key", "meta_concept:named_events_max")
        tmp.set("value", str(max_events))



