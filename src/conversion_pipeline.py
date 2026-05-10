"""
This files builds the actual file conversion pipeline.
It does this by doing several steps:

1. Let the user choose the folder.
2. Reading the contents of the folder.
3. Iterating through each file, reading it as a zarr array.
4. Writing each zarr array on disk with the intended file format.
"""

#################################################################
# Imports

from tkinter import Tk
from tkinter import filedialog

from extra_functions import file_reading_functions

#from __future__ import annotations
from pathlib import Path


class conversion_pipeline:

    ##############################################
    # Main function for conversion

    def conversion(
            output_file_format
    ):
        """
        Does the conversion algorithm, from folder choice, to reading as a zarr array, and writing as the intended format.
        This function should then be called in the GUI to be properly used.
        """


        files, n_files, folder_path = conversion_pipeline.folder_choice()

        return files
    
    ##############################################
    # Helper functions

    def files_from_folder(folder_path):
        """
        Gets all files with the intended file formats that exist in the specified folder.
        """
        
        folder = Path(folder_path)

        print("Selected folder:", folder)

        # Currently supported: .ims, .ome.zarr, .lif, ome.tiff
        file_extensions = (".ome.tiff", ".ims", ".lif")
        folder_extensions = (".ome.zarr", ".zarr")

        files = []

        for file in folder.iterdir():

            name = file.name.lower()

            if file.is_file() and name.lower().endswith(file_extensions):
                files.append(file)

            elif file.is_dir() and name.endswith(folder_extensions):
                files.append(file)

        return sorted(files)
    
    def folder_choice():
        """
        Open the window to choose the folder and screen it for .ims files
        """

        are_there_microscopy_files = False

        # Repeat the process if the user chooses a folder with no .ims files
        while are_there_microscopy_files == False:

            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)  # makes dialog appear in front

            # Open folder selection dialog
            folder_path = filedialog.askdirectory()

            # if the user cancels the dialog, exit the program
            if not folder_path:
                print("No folder selected. Exiting the program.")
                exit()

            # Destroy root
            root.destroy()

            files = file_reading_functions_class.files_from_folder(folder_path)

            if len(files) != 0:
                are_there_microscopy_files = True
            else:
                print("No microscopy files found in this folder.", flush=True)
                print("Choose another folder.")
                print()
            
        n_files = len(files)
        print(f"Found {n_files} microscopy files.")

        return files, n_files, folder_path
    
    def create_converted_output_folder(input_folder):
        """
        Creates a "Converted Files" folder inside the input folder
        Returns the created output folder path
        """

        input_folder = Path(input_folder)

        output_folder = input_folder / "Converted Files"
        output_folder.mkdir(parents=True, exist_ok=True)

        return output_folder
    
    def create_output_file(output_folder, input_file_path, output_file_format):
        """
        Creates the output file path inside the "Converted Files" folder
        """

        output_folder = Path(output_folder)
        input_file_path = Path(input_file_path)

        if not output_file_format.startswith("."):
            output_file_format = "." + output_file_format

        input_name = input_file_path.name
        lower_name = input_name.lower()

        input_file_formats = (
            ".ome.tiff",
            ".ome.zarr",
            ".ims",
            ".lif",
            ".tiff",
            ".d2",
            ".zvi",
            ".zarr",
        )

        base_name = None

        for input_file_format in input_file_formats:
            if lower_name.endswith(input_file_format):
                base_name = input_name[:-len(input_file_format)]
                break

        if base_name is None:
            base_name = input_file_path.stem

        output_file = output_folder / f"{base_name}{output_file_format}"

        return output_file
    
    def get_reader_function(input_file_path):
        """
        Selects the correct function to read the file given its format
        """

        input_file_path = Path(input_file_path)
        input_name = input_file_path.name.lower()

        READER_FUNCTIONS = {
            ".ims": file_reading_functions.read_ims_as_dask,
            ".ome.tiff": file_reading_functions.read_ometiff_as_dask,
            ".ome.zarr": file_reading_functions.read_omezarr_as_dask,
            ".lif": file_reading_functions.read_lif_as_dask,
        }

        for input_file_format, reader_function in READER_FUNCTIONS.items():
            if input_name.endswith(input_file_format):
                return reader_function

        raise ValueError(f"Unsupported file format: {input_file_path}")


if __name__ == "__main__":

    READER_FUNCTIONS = {
        ".ims": file_reading_functions.read_ims_as_dask,
        ".ome.tiff": file_reading_functions.read_ometiff_as_dask,
        ".ome.zarr": file_reading_functions.read_omezarr_as_dask,
        ".lif": file_reading_functions.read_lif_as_dask,
    }

    # This will essentially be the code that will be in the "conversion" function

    input_path = Path(
        r"C:\Users\simao\Desktop\teste"
    )

    input_file_paths = conversion_pipeline.files_from_folder(input_path)

    # Create an output folder
    output_folder = conversion_pipeline.create_converted_output_folder(input_path)
    print(output_folder)

    for input_file_path in input_file_paths:
        output_file = conversion_pipeline.create_output_file(output_folder, input_file_path, ".ome.zarr")

        print(output_file)

        img_array, pixel_size_metadata, img_axes = file_reading_functions.read_lif_as_dask(input_path)
