import json
import os.path
import sys
import threading
import logging
import traceback

from src.jilg.Main.Main import Main
from src.jilg.Other import Global

if __name__ == "__main__":
    if len(sys.argv) == 1:
        try:
            logging.basicConfig(filename=os.getcwd() + '/src/log.log', level=logging.ERROR, format='%(levelname)s: %(message)s')
        except:
            logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

        from src.jilg.UI.Gui import MainGui
        gui = MainGui()

    else:
        logging.basicConfig(level=logging.ERROR)
        config_file_path = sys.argv[1]
        if os.path.isfile(config_file_path):
            main = Main()
            loading_config_file_failed = False
            try:
                with open(config_file_path) as config_file:
                    json_data = json.load(config_file)
                    model_file_path = json_data["model_file_path"]
                    output_dir = json_data["output_directory"]
            except:
                Global.log_error(__file__, "An error occurred while reading the configuration"
                                           " file!", traceback)
                loading_config_file_failed = True
            if not loading_config_file_failed:
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
                            Global.log_error(__file__, "An error occurred while parsing the"
                                                            " configuration file to configure the"
                                                            " simulation!", traceback)
                        if not stop:
                            main.config.configure_variables_and_transitions(main.model)
                            print("Running the simulation!")
                            main.run_simulation(write_event_logs=True,
                                                command_line_mode=True,
                                                gui_lock=threading.Lock())
                    else:
                        print("The model could not be loaded due to the following errors: ")
                        for error in errors:
                            print(error)
                else:
                    print("Model path is '{path}' invalid".format(path=model_file_path))
        else:
            print("Config file path invalid!")
