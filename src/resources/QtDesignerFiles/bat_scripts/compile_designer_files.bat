cd %~dp0
cd ..
pyside6-uic MainWindow.ui -o MainWindow.py
pyside6-uic IncludedVariablesInput.ui -o IncludedVariablesInput.py
pyside6-uic TransitionsInput.ui -o TransitionsInput.py
pyside6-uic VariableInputBool.ui -o VariableInputBool.py
pyside6-uic VariableInputDate.ui -o VariableInputDate.py
pyside6-uic VariableInputDouble.ui -o VariableInputDouble.py
pyside6-uic VariableInputInt.ui -o VariableInputInt.py
pyside6-uic VariableInputString.ui -o VariableInputString.py
pyside6-uic WelcomeScreen.ui -o WelcomeScreen.py