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

from PySide6.QtWidgets import QApplication, QFileDialog
from conversion_functions import file_reading_functions, writing_functions
from pathlib import Path
import traceback


class file_conversion:

    ##############################################
    # Main function for conversion

    def batch_conversion(
            output_file_format
    ):
        """
        Does the conversion algorithm, from folder choice, to reading as a zarr array, and writing as the intended format.
        This function should then be called in the GUI to be properly used.
        """

        print("ALM Microscopy File Converter")
        print("==============================")

        # Let the user choose its folder
        input_file_paths, n_files, input_folder = file_conversion.folder_choice()

        # If no folder was selected, cancel the conversion
        if input_folder is None:
            return
        
        print(f"Selected Folder: {input_folder}")
        
        # Get the output "Conversion Folder"
        output_folder = file_conversion.create_converted_output_folder(input_folder)

        # Report metrics
        successful_files = 0
        failed_files = 0
        failed_files_report = []

        for file_index, input_file_path in enumerate(input_file_paths, start=1):

            # try/except to continue the loop even if there is any error
            try:

                print()
                print(f"Converting file {file_index}/{n_files}: {input_file_path.name}")

                output_file = file_conversion.create_output_file_path(
                    output_folder,
                    input_file_path,
                    output_file_format,
                )

                # Get the appropriate reader function for the specific input file format
                reader_function = file_conversion.get_reader_function(input_file_path)

                # Suppress unncessessary reading prints:
                with writing_functions.suppress_console_output():
                    # Apply the reader function to read the file
                    img_array, pixel_size_metadata, img_axes = reader_function(input_file_path)

                # Normalize the axes of the data
                img_array = writing_functions.normalize_to_tczyx(img_array, img_axes)

                # Get the appropriate writer function for the specific file format that was chosen
                writer_function = file_conversion.get_writer_function(output_file_format)

                # Suppress unncessessary writing prints:
                # Apply the suppress printing function
                with writing_functions.suppress_console_output():

                    # Apply the writer function to create the converted file
                    writer_function(
                        output_file,
                        img_array,
                        img_array.shape,
                        img_axes,
                        pixel_size_metadata,
                    )

                print(f"Saved file: {output_file.name}")

                successful_files += 1

            except Exception as error:
                print(f"Failed to convert file: {input_file_path.name}")
                print(f"Skipping to next file.")
                print()

                # Add report information
                failed_files += 1
                failed_files_report.append({
                    "file": input_file_path.name,
                    "error": traceback.format_exc()
                })

        file_conversion.create_report(
            output_folder,
            n_files,
            successful_files,
            failed_files,
            failed_files_report,
        )

        print()
        print("Conversion finished.")
        if failed_files == 0:
            print("All files were successfully converted.")
        else:
            print(f"Successful Files: {successful_files}/{n_files}")
            print(f"Failed Files: {failed_files}/{n_files}")




    ##############################################
    # Helper functions

    def folder_choice():
        """
        Open a PySide6 dialog to choose a folder and screen it for microscopy files.
        """

        # Start a bool variable to detect the presence of microscopy files
        are_there_microscopy_files = False

        app = QApplication.instance() or QApplication([])

        # Start a loop for file detection
        while are_there_microscopy_files == False:

            # Open a window to select a folder
            folder_path = QFileDialog.getExistingDirectory(
                None,
                "Select Folder containing microscopy files",
            )

            # If no folder was selected, simply cancel the conversion
            if not folder_path:
                print("No folder selected.")
                return [], 0, None

            # Introduce the Path variable
            folder_path = Path(folder_path)

            # Compute the microscopy files that are present
            files = file_conversion.files_from_folder(folder_path)

            # Check if there are actually any microscopy files
            if len(files) != 0:
                are_there_microscopy_files = True
            else:
                print("No microscopy files found in this folder.", flush=True)
                print("Choose another folder.")
                print()

        n_files = len(files)
        print(f"Found {n_files} Microscopy Files.")

        return files, n_files, folder_path

    
    def files_from_folder(folder_path):
        """
        Gets all files with the intended file formats that exist in the specified folder.
        """
        
        folder = Path(folder_path)

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
    
    
    def create_converted_output_folder(input_folder):
        """
        Creates a "Converted Files" folder inside the input folder
        Returns the created output folder path
        """

        input_folder = Path(input_folder)

        output_folder = input_folder / "Converted Files"
        output_folder.mkdir(parents=True, exist_ok=True)

        return output_folder
    
    def create_output_file_path(output_folder, input_file_path, output_file_format):
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
    
    def get_writer_function(output_file_format):
        """
        Selects the correct function to write the file given the file format that was chosen
        """

        WRITER_FUNCTIONS = {
            ".ome.zarr": writing_functions.write_ome_zarr,
        }

        if output_file_format in WRITER_FUNCTIONS:
                return WRITER_FUNCTIONS[output_file_format]
        
        raise ValueError(f"Unsupported output file format: {output_file_format}")
    
    def create_report(output_folder, n_files, successful_files, failed_files, failed_file_reports):
        """
        Creates a report listing the errors for failed files
        """

        # Immediately leave this function if there are no failed files
        if failed_files == 0:
            return
        
        # Create the report file
        report_file = Path(output_folder) / "conversion_report.txt"

        with open(report_file, "w", encoding="utf-8") as report:
            report.write("Conversion Report\n")
            report.write("=================\n\n")
            report.write(f"Total files: {n_files}\n")
            report.write(f"Successful files: {successful_files}\n")
            report.write(f"Failed files: {failed_files}\n\n")

            report.write("Failed file details:\n")
            report.write("--------------------\n")

            for failed_file in failed_file_reports:
                report.write(f"File: {failed_file['file']}\n")
                report.write(f"Error: {failed_file['error']}\n\n")

        print(f"Conversion report saved to: {report_file}")

