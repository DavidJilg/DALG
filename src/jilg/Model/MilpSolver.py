import datetime
import re
from copy import deepcopy
from enum import Enum

from PySide6.QtCore import QDateTime

from src.jilg.Model.Variable import Variable, VariableTypes


class Operators(Enum):
    OR = "||"
    AND = "&&"
    EQUAL = "=="
    NOT_EQUAL = "!="

    GREATER = ">"
    GREATER_EQUAL = ">="
    LESSER = "<"
    LESSER_EQUAL = "<="

    MINUS = "-"
    PLUS = "+"
    TIMES = "*"
    DIVIDE = "/"

    NONE = ""


class MilpSolver:
    operator_values = [">", "<", "-", "+", "*", "/", "&&", "||", "==", "!=", "<=", ">="]
    operators_last = [Operators.AND, Operators.OR, Operators.EQUAL, Operators.NOT_EQUAL]
    operators_last_single = [Operators.GREATER_EQUAL, Operators.LESSER_EQUAL, Operators.GREATER,
                             Operators.LESSER]
    operators_math = [Operators.MINUS, Operators.PLUS, Operators.TIMES, Operators.DIVIDE]
    variables: list
    variables_names: list

    def __init__(self):
        self.variables = []
        self.variables_names = []

    def compile_and_evaluate_string(self, guard_string, variables):
        self.__init__()
        self.variables = deepcopy(variables)
        if guard_string is None:
            return True
        guard_string = self.remove_spaces(guard_string).replace('\n', '')
        if guard_string == "":
            return True
        guard_string = self.check_for_negative_numbers(guard_string)
        for variable in self.variables:
            self.variables_names.append(variable.name)
            if not variable.has_current_value:
                if variable.name in guard_string:
                    guard_string = self.deal_with_missing_values(guard_string, variable.name)
        # print(guard_string)
        # for var in variables:
        #     print(var.name, var.value)
        # print(self.evaluate_guard_string(guard_string))
        # print("-----------------------------------------")
        return self.evaluate_guard_string(guard_string)

    def deal_with_missing_values(self, guard_string, variable_name):
        edited_string = guard_string
        index = edited_string.find(variable_name)
        while index != -1:
            edited_string = self.replace_missing_value(edited_string, index, variable_name)
            index = edited_string.find(variable_name)
        return edited_string

    def replace_missing_value(self, string, index, variable_name):
        true_string = 'true'
        false_string = 'false'
        if "(" in string:
            left_bracket_index, right_bracket_index = self.find_brackets(string, index,
                                                                         len(variable_name))
            if left_bracket_index == 0:
                left_string = "("
            else:
                left_string = string[0:left_bracket_index+1]
            if right_bracket_index == len(string)-1:
                right_string = ")"
            else:
                right_string = string[right_bracket_index:]
            replacement_part = string[left_bracket_index+1: right_bracket_index]

        else:
            replacement_part = string
            left_string, right_string = "", ""

        if "!=" in replacement_part:
            replacement_part = true_string
            return left_string+replacement_part+right_string
        else:
            replacement_part = false_string
            return left_string + replacement_part + right_string

    def find_brackets(self, string, index, var_length):
        left_index = -1
        right_index = -1
        current_index = index
        bracket_count = 0
        while current_index >= 0:
            if string[current_index] == "(" and bracket_count == 0:
                left_index = current_index
                break
            elif string[current_index] == ")":
                bracket_count += 1
                current_index -= 1
            elif string[current_index] == "(":
                bracket_count -= 1
                current_index -= 1
            else:
                current_index -= 1

        bracket_count = 0
        current_index = index + var_length
        while current_index < len(string):
            if string[current_index] == ")" and bracket_count == 0:
                right_index = current_index
                break
            elif string[current_index] == "(":
                bracket_count += 1
                current_index += 1
            elif string[current_index] == ")":
                bracket_count -= 1
                current_index += 1
            else:
                current_index += 1
        return left_index, right_index

    def remove_spaces(self, string):
        lst = string.split('"')
        for i, item in enumerate(lst):
            if not i % 2:
                lst[i] = re.sub("\s+", "", item)
        return '"'.join(lst)

    def check_for_negative_numbers(self, guard_string):
        minus_indices = self.check_for_non_operator_minuses(guard_string)
        if not minus_indices:
            return guard_string
        else:
            return self.replace_negative_numbers_and_add_variables(guard_string, minus_indices)

    def check_for_non_operator_minuses(self, guard_string):
        single_minuses_indices = []
        for index, char in enumerate(guard_string):
            if char == '-':
                if self.is_single_minus(guard_string, index):
                    single_minuses_indices.append(index)
        return single_minuses_indices

    def replace_negative_number(self, guard_string, var_index, index_deviation, variable_tupels,
                                minus_index):
        start_index = minus_index + index_deviation
        rep_var = "-"
        while True:
            if minus_index + index_deviation + 1 == len(guard_string):
                minus_index += 1
                break
            else:
                minus_index += 1
            current_char = guard_string[minus_index + index_deviation]
            if self.is_operator_char(current_char):
                break
            else:
                rep_var += current_char
        var_tupel = ("______RV_______" + str(var_index), int(rep_var))
        variable_tupels.append(var_tupel)
        guard_string = guard_string[0:start_index] + "______RV_______" + str(var_index) + \
                       guard_string[minus_index + index_deviation:]
        index_deviation += len(var_tupel[0]) - len(rep_var)
        var_index += 1
        return guard_string, var_index, index_deviation, variable_tupels

    def replace_negative_numbers(self, guard_string, indices):
        var_index = 0
        index_deviation = 0
        variable_tupels = []
        for minus_index in indices:
            guard_string, var_index, index_deviation, variable_tupels = self.replace_negative_number(
                guard_string,
                var_index,
                index_deviation,
                variable_tupels,
                minus_index)
        return guard_string, variable_tupels

    def replace_negative_numbers_and_add_variables(self, guard_string, indices):
        guard_string, variable_tupels = self.replace_negative_numbers(guard_string, indices)
        for variable_tuple in variable_tupels:
            self.variables.append(
                Variable(variable_tuple[0], VariableTypes.DOUBLE.value, None, None,
                         None, None, None, None, float(variable_tuple[1]), True)
            )
        return guard_string

    def is_operator_char(self, char):
        for operator_value in self.operator_values:
            if operator_value[0] == char:
                return True
        if char == ')':
            return True
        return False

    def is_single_minus(self, guard_string, index):
        string = ""
        while True:
            index -= 1
            if index < 0:
                return False
            string = guard_string[index] + string
            if string in self.operator_values or string == '(':
                return True

    def check_for_single_value(self, guard_string):
        for operator in self.operator_values:
            if operator != "-" and operator != "+" and operator in guard_string:
                return None
        if guard_string in self.variables_names:
            return self.variable_value_by_name(guard_string)
        elif self.check_int(guard_string):
            return int(guard_string)
        elif self.check_float(guard_string):
            return float(guard_string)
        elif self.check_string(guard_string):
            try:
                date = QDateTime.fromString(guard_string[1:-1], "yyyy-MM-ddThh:mm:ss")
                if date.isNull():
                    return guard_string[1:-1]
                else:
                    return date.toSecsSinceEpoch()
            except:
                return guard_string[1:-1]

        elif guard_string in ["FALSE", "false", "False"]:
            return False
        elif guard_string in ["TRUE", "true", "True"]:
            return True
        return None

    def evaluate_guard_string(self, guard_string, brackets=None):
        if brackets is None:
            brackets = []
        if '(' in guard_string or ')' in guard_string:
            guard_string, brackets = self.replace_brackets(guard_string, brackets)
            return self.evaluate_guard_string(guard_string, brackets)
        else:
            value = self.check_for_single_value(guard_string)
            if value is not None:
                return value
            else:
                return self.deal_with_operators(guard_string, brackets)

    def deal_with_operators(self, guard_string, brackets):
        for operator in self.operators_last:
            if self.only_one_operator_type(guard_string, operator):
                return self.evaluate_brackets(guard_string, brackets, operator)
        for operator in self.operators_last_single:
            if self.only_one(guard_string, operator):
                return self.evaluate_brackets(guard_string, brackets, operator)
        for operator in self.operators_math:
            if self.only_one_operator_type(guard_string, operator):
                return self.evaluate_brackets(guard_string, brackets, operator)
        if self.no_operators_in_string(guard_string):
            return self.evaluate_brackets(guard_string, brackets, Operators.NONE)
        print("THIS SHOULD NOT BE REACHED! Guard String:" + guard_string)

    def evaluate_brackets_with_and(self, parts, brackets):
        for part in parts:
            if not self.evaluate_guard_string(part, brackets):
                return False
        return True

    def evaluate_brackets_with_or(self, parts, brackets):
        for part in parts:
            if self.evaluate_guard_string(part, brackets):
                return True
        return False

    def evaluate_brackets_with_equal(self, parts, brackets):
        results = []
        for part in parts:
            results.append(self.evaluate_guard_string(part, brackets))
        for i in range(1, len(results)):
            if results[0] != results[i]:
                return False
        return True

    def evaluate_brackets_with_not_equal(self, parts, brackets):
        results = []
        for part in parts:
            results.append(self.evaluate_guard_string(part, brackets))
        for i in range(1, len(results)):
            if results[0] == results[i]:
                return False
        return True

    def evaluate_brackets_with_last_operator(self, parts, brackets, operator):
        if operator == Operators.AND:
            return self.evaluate_brackets_with_and(parts, brackets)
        elif operator == Operators.OR:
            return self.evaluate_brackets_with_or(parts, brackets)
        elif operator == Operators.EQUAL:
            return self.evaluate_brackets_with_equal(parts, brackets)
        elif operator == Operators.NOT_EQUAL:
            return self.evaluate_brackets_with_not_equal(parts, brackets)

    def evaluate_brackets_with_last_single_operator(self, parts, brackets, operator):
        part0 = self.evaluate_guard_string(parts[0], brackets)
        part1 = self.evaluate_guard_string(parts[1], brackets)
        if type(part0) not in [int, float] or type(part1) not in [int, float]:
            return False
        elif operator == Operators.GREATER:
            return part0 > part1
        elif operator == Operators.GREATER_EQUAL:
            return part0 >= part1
        elif operator == Operators.LESSER:
            return part0 < part1
        elif operator == Operators.LESSER_EQUAL:
            return part0 <= part1

    def evaluate_brackets_with_minus(self, parts, brackets):
        value = self.evaluate_guard_string(parts[0], brackets)
        if type(value) not in [int, float]:
            return False
        for index, part in enumerate(parts):
            if index != 0:
                tmp = self.evaluate_guard_string(parts[index], brackets)
                if type(tmp) not in [int, float]:
                    return False
                else:
                    value -= tmp
        return value

    def evaluate_brackets_with_plus(self, parts, brackets):
        value = self.evaluate_guard_string(parts[0], brackets)
        if type(value) not in [int, float]:
            return False
        for index, part in enumerate(parts):
            if index != 0:
                tmp = self.evaluate_guard_string(parts[index], brackets)
                if type(tmp) not in [int, float]:
                    return False
                else:
                    value += self.evaluate_guard_string(parts[index], brackets)
        return value

    def evaluate_brackets_with_times(self, parts, brackets):
        value = self.evaluate_guard_string(parts[0], brackets)
        if type(value) not in [int, float]:
            return False
        for index, part in enumerate(parts):
            if index != 0:
                tmp = self.evaluate_guard_string(parts[index], brackets)
                if type(tmp) not in [int, float]:
                    return False
                else:
                    value *= self.evaluate_guard_string(parts[index], brackets)
        return value

    def evaluate_brackets_with_divide(self, parts, brackets):
        value = self.evaluate_guard_string(parts[0], brackets)
        if type(value) not in [int, float]:
            return False
        for index, part in enumerate(parts):
            if index != 0:
                tmp = self.evaluate_guard_string(parts[index], brackets)
                if type(tmp) not in [int, float]:
                    return False
                else:
                    value /= self.evaluate_guard_string(parts[index], brackets)
        return value

    def evaluate_brackets_with_arithmetic_operator(self, parts, brackets, operator):
        if operator == Operators.MINUS:
            return self.evaluate_brackets_with_minus(parts, brackets)
        elif operator == Operators.PLUS:
            return self.evaluate_brackets_with_plus(parts, brackets)
        elif operator == Operators.TIMES:
            return self.evaluate_brackets_with_times(parts, brackets)
        elif operator == Operators.DIVIDE:
            return self.evaluate_brackets_with_divide(parts, brackets)

    def evaluate_brackets(self, guard_string, brackets, operator):
        if operator != Operators.NONE:
            parts = guard_string.split(operator.value)
            if operator in self.operators_last:
                return self.evaluate_brackets_with_last_operator(parts, brackets, operator)
            elif operator in self.operators_last_single:
                return self.evaluate_brackets_with_last_single_operator(parts, brackets, operator)
            else:
                return self.evaluate_brackets_with_arithmetic_operator(parts, brackets, operator)
        else:
            return self.evaluate_bracket(guard_string, brackets)

    def check_int(self, string):
        if string[0] in ('-', '+'):
            return string[1:].isdigit()
        return string.isdigit()

    def check_float(self, string):
        try:
            float(string)
            return True
        except:
            return False

    def check_string(self, string):
        if string.count("'") == 2 or string.count('"') == 2:
            return True
        else:
            return False

    def variable_value_by_name(self, name):
        for variable in self.variables:
            if name == variable.name:
                if variable.has_current_value:
                    if variable.type == VariableTypes.DATE:
                        return variable.value
                    else:
                        return variable.value
                else:
                    return self.replacement_value(variable)
        else:
            return None

    def replacement_value(self, variable):
        if variable.type == VariableTypes.DATE:
            return 253370761260
        elif variable.type in [VariableTypes.INT, VariableTypes.LONG]:
            return -123456789
        elif variable.type == VariableTypes.STRING:
            return "__UNDEFINED1701__"
        elif variable.type == VariableTypes.BOOL:
            return False
        elif variable.type == VariableTypes.DOUBLE:
            return -123456789.0

    def evaluate_bracket(self, guard_string, brackets):
        bracket_id = int(guard_string[7:])
        return self.evaluate_guard_string(brackets[bracket_id], brackets)

    def only_one(self, string, operator):
        return string.count(operator.value) == 1

    def only_one_operator_type(self, string, given_operator):
        if given_operator.value in string:
            for operator in Operators:
                if operator != given_operator and operator != Operators.NONE:
                    if operator.value in string:
                        return False
            return True
        else:
            return False

    def no_operators_in_string(self, string):
        for operator in Operators:
            if not operator == Operators.NONE:
                if operator.value in string:
                    return False
        return True

    def only_and_operator_type(self, string):
        return (Operators.AND.value in string) and \
               (Operators.NOT_EQUAL.value not in string) and \
               (Operators.OR.value not in string) and \
               (Operators.EQUAL.value not in string)

    def only_or_operator_type(self, string):
        return (Operators.OR.value in string) and \
               (Operators.AND.value not in string) and \
               (Operators.NOT_EQUAL.value not in string) and \
               (Operators.EQUAL.value not in string)

    def only_equal_operator_type(self, string):
        return (Operators.EQUAL.value in string) and \
               (Operators.AND.value not in string) and \
               (Operators.OR.value not in string) and \
               (Operators.NOT_EQUAL.value not in string)

    def only_notequal_operator_type(self, string):
        return (Operators.NOT_EQUAL.value in string) and \
               (Operators.AND.value not in string) and \
               (Operators.OR.value not in string) and \
               (Operators.EQUAL.value not in string)

    def replace_brackets(self, string, bracket_list):
        bracketListIndex = len(bracket_list)
        while '(' in string:
            firstBracketIndex = string.find('(')
            bracketIndex = firstBracketIndex + 1
            bracketCount = 1
            while bracketCount != 0:
                if string[bracketIndex] == '(':
                    bracketCount += 1
                elif string[bracketIndex] == ')':
                    bracketCount -= 1
                bracketIndex += 1
            bracket_list.append(string[firstBracketIndex + 1:bracketIndex - 1])
            string = string[0:firstBracketIndex] + "bracket" + str(bracketListIndex) + string[
                                                                                       bracketIndex:]
            bracketListIndex += 1
        return string, bracket_list


if __name__ == "__main__":
    lc = MilpSolver()
    variables = [Variable("varDate", "java.util.Date", 0, 0, 0, 0, None, None, None, False)]
    variables[0].value = 1088874282.7827098
    variables[0].has_current_value = True
    variables[0].has_been_written_to = True
    print(lc.compile_and_evaluate_string('(varDate > "2003-01-01T00:00:00")', variables))
