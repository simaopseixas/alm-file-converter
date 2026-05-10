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

class conversion_pipeline:

    def conversion(
            output_file_format
    ):
        """
        Does the conversion algorithm, from folder choice, to reading as a zarr array, and writing as the intended format.
        This function should then be called in the GUI to be properly used.
        """
        
        READER_FUNCTIONS = {
            ".ims": file_reading_functions.read_ims_as_zarr,
            ".ome.tiff": file_reading_functions.read_ometiff_as_zarr,
            ".ome.zarr": file_reading_functions.read_zarr,
            ".zarr": file_reading_functions.read_zarr
        }

        files, n_files, folder_path = conversion_pipeline.folder_choice()

        return files
    
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
        

if __name__ == "__main__":

    files = conversion_pipeline.conversion(".ims")

    print(files)
