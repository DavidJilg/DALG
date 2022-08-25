import json
import os.path
import sys
import threading

from src.jilg.Main.Main import Main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        from src.jilg.UI.Gui import MainGui
        gui = MainGui()
    else:
        config_file_path = sys.argv[1]
        if os.path.isfile(config_file_path):
            main = Main()
            try:
                with open(config_file_path) as config_file:
                    json_data = json.load(config_file)
                    model_file_path = json_data["model_file_path"]
                    output_dir = json_data["output_directory"]
            except:
                print("An error occurred while reading the configuration file!")
            if os.path.isfile(model_file_path):
                print(" \nTrying to load {path}\n ".format(path=model_file_path))
                main.model_path = model_file_path
                success, errors = main.initialize_model_and_config(output_dir)
                if success:
                    if errors:
                        print("Successfully loaded model but the following problems occured:")
                        for error in errors:
                            print(error)
                    else:
                        print("Successfully loaded model!")
                    try:
                        stop = False
                        main.config.read_config_file(config_file_path, main.model, True)
                    except:
                        stop = True
                        print("An error occurred while parsing the configuration file to configure"
                              "the simulation!")
                    if not stop:
                        main.config.configure_variables_and_transitions(main.model)
                        print("Running the simulation!")
                        main.run_simulation(True, False, threading.Lock())
                else:
                    print("The model could not be loaded due to the following errors: ")
                    for error in errors:
                        print(error)
            else:
                print("Model path is '{path}' invalid".format(path=model_file_path))
        else:
            print("Config file path invalid!")
