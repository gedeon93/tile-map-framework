'''
Name: Tile Map Framework
Author: Bryan Barrows
Comment: Tool template for rendering image tile layers of ArcGIS satellite imagery.
%Complete: 100
'''

import os
import sys
import argparse
import configparser

import pandas as pd

from pathlib import Path
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication

from app.MapInterface import MapInterface

COLOR_CYCLE = [
    QColor("#2CA02C"), # Green
    QColor("#1F77B4"), # Blue
    QColor("#FF7F0E"), # Orange
    QColor("#D62728"), # Red
    QColor("#9467BD"), # Purple
    QColor("#8C564B")  # Brown
]

def load_config(file: str, working_directory: str) -> dict:
    """
    Loads the .ini configuration file for the setup of data loading, storage, etc.

    Args:
        file (str): name of configuration file.
        working_directory (str): path to the main project directory.

    Returns:
        dict: dictionary of folder/file paths (strings)
    """
    config = configparser.ConfigParser()
    config.read(working_directory + file)
    working_directory = Path(working_directory[:-1])

    resource_dir = config["imports"]["resource_dir"]
    resource_dir = Path.joinpath(working_directory, resource_dir)
    paths = { key: str(resource_dir / value) for key, value in config["paths"].items() }

    data_dir = config["imports"]["data_dir"]
    data_dir = Path.joinpath(working_directory, data_dir)
    return [paths, data_dir]

def load_csv(file: str) -> pd.DataFrame:
    """
    Helper method for loading files of Comma-Separated Values type.
    """
    try:
        return pd.read_csv(file, encoding='unicode_escape')
    except FileNotFoundError:
        print(f"File not found: {file}")
    return pd.DataFrame()

if __name__== "__main__":
    # PARSE CLI ARGUMENTS:
    parser = argparse.ArgumentParser(description="Map Visualization Tool: An application of the ArcGIS image tile layer system.")
    parser.add_argument('-p', '--path', type=str, default=None, required=False,
                        help='Specify a path to the source directory where the application resides.')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, required=False,
                        help='Show all logs, warnings, and error messages.')
    args = parser.parse_args()

    current_working_directory = os.getcwd()
    if args.path:
        current_working_directory = str(args.path)
    if len(current_working_directory) < 1:
        raise Exception(f"Error: Invalid working directory '{current_working_dir}' provided.")
    current_working_directory = current_working_directory.replace("\\\\", "\\")
    current_working_directory = current_working_directory.replace("\\", "/")
    if current_working_directory[-1] != "/":
        current_working_directory += "/"
        
    verbose = False
    if args.verbose:
        verbose = args.verbose

    # PARSE CONFIG.INI:
    # resource_paths, data_dir_base = load_config("config.ini", working_directory= current_working_directory)
    
    # Load config parameters, files, data (then preprocess)

    # INITIALIZE QT AND EVENT LOOP:
    # Address command-line parsing by Qt later. No specific use currently.
    main_app = QApplication([])
    window = MapInterface()

    # Do any additional configuration: module initialization, data filtering, etc.

    window.setWindowTitle("Image Tile Layer")
    window.show()

    sys.exit(main_app.exec_())