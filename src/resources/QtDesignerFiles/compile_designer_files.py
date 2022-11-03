import os
import shutil
import subprocess


def compile_designer_files():
    subprocess.call([os.getcwd() + "/bat_scripts/compile_designer_files.bat"],
                    stdout=open(os.devnull, 'wb'))
    files = ["MainWindow.py",
             "IncludedVariablesInput.py",
             "TransitionsInput.py",
             "VariableInputBool.py",
             "VariableInputDate.py",
             "VariableInputDouble.py",
             "VariableInputInt.py",
             "VariableInputString.py",
             "WelcomeScreen.py"]

    for file in files:
        os.remove(f"../../jilg/Ui/QtDesignerClasses/{file}")
        os.rename(file, f"../../jilg/Ui/QtDesignerClasses/{file}")


if __name__ == "__main__":
    compile_designer_files()
