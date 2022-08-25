from unittest import TestCase
import unittest

from src.jilg.Model.Variable import Variable, VariableTypes
from src.jilg.Model.MilpSolver import MilpSolver


class TestMilpSolver(TestCase):
    lc: MilpSolver

    var1 = Variable("var1", VariableTypes.INT.value, None, None, None, None, None, None, 1)
    var2 = Variable("var2", VariableTypes.INT.value, None, None, None, None, None, None, 2)
    var3 = Variable("var3", VariableTypes.INT.value, None, None, None, None, None, None, 3)
    var4 = Variable("var4", VariableTypes.INT.value, None, None, None, None, None, None, 4)
    var5 = Variable("var5", VariableTypes.INT.value, None, None, None, None, None, None, 5)
    var10x = Variable("var10x", VariableTypes.INT.value, None, None, None, None, None, None, 10)

    var6 = Variable("var6", VariableTypes.STRING.value, None, None, None, None, None, None, "var6")
    var7 = Variable("var7", VariableTypes.STRING.value, None, None, None, None, None, None, "var7")
    var8 = Variable("var8", VariableTypes.STRING.value, None, None, None, None, None, None, "test")
    var9 = Variable("var9", VariableTypes.STRING.value, None, None, None, None, None, None, "test")

    var10 = Variable("var10", VariableTypes.DOUBLE.value, None, None, None, None, None, None, 1.5)
    var11 = Variable("var11", VariableTypes.DOUBLE.value, None, None, None, None, None, None, 2.5)
    var12 = Variable("var12", VariableTypes.DOUBLE.value, None, None, None, None, None, None, 3.5)
    var13 = Variable("var13", VariableTypes.DOUBLE.value, None, None, None, None, None, None, 4.5)

    variables = [var1, var2, var3, var4, var5, var6, var7, var8, var9, var10, var10x, var11, var12,
                 var13]

    def setUp(self):
        self.lc = MilpSolver()

    def test_logic_compiler(self):
        self.setUp()

        self.assertEqual(self.lc.compile_and_evaluate_string("((TRUE) || (FALSE))", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("(TRUE) || (FALSE)", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("TRUE || FALSE", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("(FALSE) || (TRUE)", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("(TRUE) || (TRUE)", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("(FALSE) || (FALSE)", self.variables), False)

        self.assertEqual(self.lc.compile_and_evaluate_string("(TRUE) && (FALSE)", self.variables), False)
        self.assertEqual(self.lc.compile_and_evaluate_string("(FALSE) && (TRUE)", self.variables), False)
        self.assertEqual(self.lc.compile_and_evaluate_string("(TRUE) && (TRUE)", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("(FALSE) && (FALSE)", self.variables), False)

        self.assertEqual(self.lc.compile_and_evaluate_string("(TRUE) == (FALSE)", self.variables), False)
        self.assertEqual(self.lc.compile_and_evaluate_string("(FALSE) == (TRUE)", self.variables), False)
        self.assertEqual(self.lc.compile_and_evaluate_string("(TRUE) == (TRUE)", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("(FALSE) == (FALSE)", self.variables), True)

        self.assertEqual(self.lc.compile_and_evaluate_string("(TRUE) != (FALSE)", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("(FALSE) != (TRUE)", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("(TRUE) != (TRUE)", self.variables), False)
        self.assertEqual(self.lc.compile_and_evaluate_string("(FALSE) != (FALSE)", self.variables), False)

        self.assertEqual(self.lc.compile_and_evaluate_string("var1 == var1", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("var1 == var2", self.variables), False)
        self.assertEqual(self.lc.compile_and_evaluate_string("var1 != var1", self.variables), False)
        self.assertEqual(self.lc.compile_and_evaluate_string("var1 != var2", self.variables), True)

        self.assertEqual(self.lc.compile_and_evaluate_string("var8 == var9", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("var6 == var7", self.variables), False)
        self.assertEqual(self.lc.compile_and_evaluate_string("var8 != var9", self.variables), False)
        self.assertEqual(self.lc.compile_and_evaluate_string("var6 != var7", self.variables), True)

        self.assertEqual(self.lc.compile_and_evaluate_string("(1 + 1) == 2", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("(1 + 1) == 3", self.variables), False)
        self.assertEqual(self.lc.compile_and_evaluate_string("(var1 + 1) == 2", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("(var1 + var1) == 2", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("(var1 + var1) == 1", self.variables), False)
        self.assertEqual(self.lc.compile_and_evaluate_string("(var1 + var2 + var3) == 6", self.variables), True)
        self.assertEqual(self.lc.compile_and_evaluate_string("(var1 + var2 + var3) == 7", self.variables), False)

        self.assertEqual(self.lc.compile_and_evaluate_string("(1 - 1) == 0", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("(var1 - 1) == 0", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("(var1 - var1) == 0", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("(var2 - var1) == 1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("(var2 - var1) == 0", self.variables), False),

        self.assertEqual(self.lc.compile_and_evaluate_string("(var1-var3)==-2", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("(var1-var3)==(-10--8)", self.variables), True),

        self.assertEqual(self.lc.compile_and_evaluate_string("(1 * 1) == 1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("(var1 * 5) == 5", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("(var3 * var2) == 6", self.variables), True),

        self.assertEqual(self.lc.compile_and_evaluate_string("(var4 / var2) == 2", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("(var5 / var10x) == 0.5", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("(var5 / var10x) == 0.6", self.variables), False),

        self.assertEqual(self.lc.compile_and_evaluate_string("1 > 0", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("var1 > 0", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("var2 > var1", self.variables), True),

        self.assertEqual(self.lc.compile_and_evaluate_string("0 < 1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("0 < var1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("var1 < var2", self.variables), True),

        self.assertEqual(self.lc.compile_and_evaluate_string("1 >= 1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("-1 >= -1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("2 >= 1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("var1 >= 1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("var1 >= 0", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("var2 >= var1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("var2 >= var2", self.variables), True),

        self.assertEqual(self.lc.compile_and_evaluate_string("1 <= 1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("-1 <= -1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("1 <= 2", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("1 <= var1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("0 <= var1", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("var1 <= var2", self.variables), True),
        self.assertEqual(self.lc.compile_and_evaluate_string("var2 <= var2", self.variables), True),

        self.assertEqual(self.lc.compile_and_evaluate_string("'test' == 'test'", self.variables), True),

        self.assertEqual(self.lc.compile_and_evaluate_string(
            "(((var1 + var3) == (var2 * var2)) && ('test' == var8)) || (((var3 /var3) == var1) && "
            "( (var2 - var1) > var1))", self.variables), True)
