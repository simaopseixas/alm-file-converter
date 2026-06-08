"""
This files builds the actual file conversion pipeline.
It does this by doing several steps:

1. Let the user choose the folder.
2. Reading the contents of the folder.
3. Iterating through each file, reading it as a zarr array.
4. Writing each zarr array on disk with the intended file format.
"""

###################################################################
# Imports

from PySide6.QtWidgets import QApplication, QFileDialog
from conversion_functions import file_reading_functions, writing_functions
from pathlib import Path
import traceback
from datetime import datetime
import gc

#------------------------------------------------------------------
# Fallback logger in case I want to use the conversion functions independently without the GUI
class ConsoleLogger:

    def print(self, *args, sep=" ", end="\n", flush=False):
        print(*args, sep=sep, end=end, flush=flush)


###################################################################
# Conversion Algorithms

class file_conversion:

    ##############################################
    # Functions for conversion

    #------------------------------------------
    # Batch Conversion

    def batch_conversion(output_file_format, input_file_paths=None, n_files=None, input_folder=None, logger=None):
        """
        Performs the conversion algorithm for a batched conversion
        From folder choice, reading as a dask array, and writing as the intended format.
        """

        # Give the logging
        logger = logger or ConsoleLogger()

        logger.print()
        logger.print("-------------------------------------------------------------------------------------------------------------------------------------------------------------------")
        logger.print("Batch Conversion:")
        logger.print("-------------------------------------------------------------------------------------------------------------------------------------------------------------------")

        # If the folder was not yet chosen, let the user choose it
        if input_file_paths is None or n_files is None or input_folder is None:
            input_file_paths, n_files, input_folder = file_conversion.folder_choice(logger=logger)

        # If no folder was selected, cancel the conversion
        if input_folder is None:
            return
        
        logger.print()
        logger.print(f"Selected Folder: {input_folder}")
        logger.print(f"Found {n_files} Microscopy Files.")

        # Create a "Converted Files" folder that includes the output file format (e.g. "Converted Filed OME ZARR")
        output_format_name = output_file_format.removeprefix(".").replace(".", " ").upper()
        output_folder = Path(input_folder) / f"Converted Files {output_format_name}"
        output_folder.mkdir(parents=True, exist_ok=True)

        # Report metrics
        successful_files = 0
        failed_files = 0
        failed_files_report = []

        for file_index, input_file_path in enumerate(input_file_paths, start=1):

            # Get the disk space that the file occupies
            file_size = file_conversion.get_disk_space(input_file_path)

            logger.print()
            logger.print(f"Converting file {file_index}/{n_files}: {input_file_path.name} to {output_file_format} ({file_size})")

            conversion_failed = False
            error_message = None
            error_traceback = None
            output_file = None
            image_series = None
            close_after_write_functions = []

            # try/except to continue the loop even if there is any error
            with writing_functions.suppress_console_output():

                try:

                    # Create the appropriate file path
                    output_file = file_conversion.create_output_file_path(output_folder, input_file_path, output_file_format)

                    # Get the appropriate reader function for the specific input file format
                    reader_function = file_conversion.get_reader_function(input_file_path)

                    # Apply the reader function to read the file
                    image_series = reader_function(input_file_path)

                    # Get the closing function if it exists on the dictionary
                    close_after_write_functions = [
                        series["file_close_function"]
                        for series in image_series
                        if "file_close_function" in series
                    ]

                    # Normalize all available series
                    for series in image_series:
                        series["array"], series["axes"] = writing_functions.normalize_to_tczyx(series["array"], series["axes"])

                    # Get the appropriate writer function for the specific file format that was chosen
                    writer_function = file_conversion.get_writer_function(output_file_format)

                    # Apply the writer function to create the converted file
                    writer_function(output_file, image_series)


                except Exception as error:
                    conversion_failed = True
                    error_message = str(error)
                    error_traceback = traceback.format_exc()

                finally:
                    # Close any open nd2 or ims file
                    for close_function in close_after_write_functions:
                        close_function()

                # Garbage collect
                gc.collect()

            # Final prints of the file and failed status for the report
            if conversion_failed:

                # Append the file and the error to the report dictionary
                failed_files_report.append({
                    "file": input_file_path.name,
                    "error": error_traceback,
                })
                failed_files += 1

                logger.print(f"Failed to convert file: {input_file_path.name}")
                logger.print(f"Error: {error_message}")
                logger.print("Skipping to next file.")

            else:
                successful_files += 1

                # Different prints for different cases
                if image_series is not None and len(image_series) > 1 and output_file_format in (".tif", ".tiff"):
                    output_format_name = output_file.suffix.replace(".", "")
                    logger.print(
                        f"Saved files to: "
                        f"{output_file.name.removesuffix(output_file.suffix)}_{output_format_name}"
                    )

                elif image_series is not None and len(image_series) > 1 and output_file_format == ".ome.zarr":
                    logger.print(f"Saved files to: {output_file.name.removesuffix('.ome.zarr')}_omezarr")

                else:
                    logger.print(f"Saved File: {output_file.name}")

        # Create the final report
        file_conversion.create_report(
            output_folder,
            n_files,
            successful_files,
            failed_files,
            failed_files_report,
            logger=logger,
        )

        logger.print()
        logger.print("Conversion finished.")
        if failed_files == 0:
            logger.print("All files were successfully converted.")
            logger.print("-------------------------------------------------------------------------------------------------------------------------------------------------------------------")
        else:
            logger.print("-------------------------------------------------------------------------------------------------------------------------------------------------------------------")
            logger.print(f"Successful Files: {successful_files}/{n_files}")
            logger.print(f"Failed Files: {failed_files}/{n_files}")
            logger.print("Some files failed to convert. Check the conversion report for details.")
            logger.print("-------------------------------------------------------------------------------------------------------------------------------------------------------------------")

    #------------------------------------------
    # Single-File Conversion

    def single_file_conversion(output_file_format, input_file_path=None, logger=None):
        """
        Performs the conversion algorithm for a single file.
        From file choice, reading as a dask array and writing as the intended format.
        """

        # Give the logger
        logger = logger or ConsoleLogger()

        # If the file was not yet chosen, let the user choose it
        if input_file_path is None:
            input_file_path = file_conversion.file_choice(logger=logger)

        # If the user closes the dialog, cancel the conversion
        if input_file_path is None:
            return
        
        # Get the disk space that the file occupies
        file_size = file_conversion.get_disk_space(input_file_path)
        
        logger.print()
        logger.print("-------------------------------------------------------------------------------------------------------------------------------------------------------------------")
        logger.print(f"Converting File: {input_file_path.name} to {output_file_format} ({file_size})")

        conversion_failed = False
        error_message = None
        error_traceback = None
        output_file = None
        image_series = None
        close_after_write_function = []

        # Get the output "Conversion Folder" before the reading happens
        output_folder = file_conversion.create_converted_output_folder(input_file_path.parent)

        # Suppress unnecessary reading prints:
        with writing_functions.suppress_console_output():

            try:

                # Get the appropriate reader function for the specific input file format
                reader_function = file_conversion.get_reader_function(input_file_path)

                # Apply the reader function to read the file
                image_series = reader_function(input_file_path)

                # Get the closing function if it exists on the dictionary
                close_after_write_function = [
                    series["file_close_function"]
                    for series in image_series
                    if "file_close_function" in series
                ]

                # Create the appropriate file path
                output_file = file_conversion.create_output_file_path(output_folder, input_file_path, output_file_format)

                # Normalize the axes of each available series
                for series in image_series:
                    series["array"], series["axes"] = writing_functions.normalize_to_tczyx(series["array"], series["axes"])

                # Get the appropriate writer function for the specific file format that was chosen
                writer_function = file_conversion.get_writer_function(output_file_format)

                # Apply the writer function to create the converted file
                writer_function(output_file, image_series)

            except Exception as error:
                conversion_failed = True
                error_message = str(error)
                error_traceback = traceback.format_exc()

            finally:
                # Close any open nd2 or ims file
                for close_function in close_after_write_function:
                    close_function()

            # Garbage collect
            gc.collect()

        if conversion_failed:
            logger.print()
            logger.print(f"Failed to convert file: {input_file_path.name}")
            logger.print(f"Error: {error_message}")
            logger.print(error_traceback.rstrip())
            logger.print()

            # Create the report file
            file_conversion.create_single_file_error_report(
                output_folder,
                input_file_path,
                error_message,
                error_traceback,
                logger=logger,
            )
            logger.print("-------------------------------------------------------------------------------------------------------------------------------------------------------------------")

        else:
            # Different prints for different cases
            if image_series is not None and len(image_series) > 1 and output_file_format in (".tif", ".tiff"):
                output_format_name = output_file.suffix.replace(".", "")
                logger.print(
                    f"Saved files to: "
                    f"{output_file.name.removesuffix(output_file.suffix)}_{output_format_name}"
                )

            elif image_series is not None and len(image_series) > 1 and output_file_format == ".ome.zarr":
                logger.print(f"Saved files to: {output_file.name.removesuffix('.ome.zarr')}_omezarr")

            else:
                logger.print(f"Saved File: {output_file.name}")
            logger.print("-------------------------------------------------------------------------------------------------------------------------------------------------------------------")
            


    def single_omezarr_conversion(output_file_format, input_file_path=None, logger=None):
        """
        Performs the conversion algorithm for a single OME-NGFF Zarr file.
        From file choice, reading as a dask array and writing as the intended format.
        """
        
        # Give the logger
        logger = logger or ConsoleLogger()


        # If the folder was not yet chosen, let the user choose it
        if input_file_path is None:
            input_file_path = file_conversion.zarr_choice(logger=logger)

        # If the user closes the dialog, cancel the conversion
        if input_file_path is None:
            return
        
        # Get the disk space that the file occupies
        file_size = file_conversion.get_disk_space(input_file_path)
        
        logger.print()
        logger.print("-------------------------------------------------------------------------------------------------------------------------------------------------------------------")
        logger.print(f"Converting File: {input_file_path.name} to {output_file_format} ({file_size})")

        conversion_failed = False
        error_message = None
        error_traceback = None
        output_file = None
        image_series = None
        close_after_write_functions = []

        # Get the output "Conversion Folder" before the reading happens
        output_folder = file_conversion.create_converted_output_folder(input_file_path.parent)

        # Suppress unnecessary reading prints:
        with writing_functions.suppress_console_output():

            try:

                # Get the appropriate reader function for the specific input file format
                reader_function = file_conversion.get_reader_function(input_file_path)

                # Apply the reader function to read the file
                image_series = reader_function(input_file_path)

                # Get the closing function if it exists on the dictionary
                close_after_write_functions = [
                    series["file_close_function"]
                    for series in image_series
                    if "file_close_function" in series
                ]

                # Create the appropriate file path
                output_file = file_conversion.create_output_file_path(output_folder, input_file_path, output_file_format)

                # Normalize the axes of each available series
                for series in image_series:
                    series["array"], series["axes"] = writing_functions.normalize_to_tczyx(series["array"], series["axes"])

                # Get the appropriate writer function for the specific file format that was chosen
                writer_function = file_conversion.get_writer_function(output_file_format)

                # Apply the writer function to create the converted file
                writer_function(output_file, image_series)

            except Exception as error:
                conversion_failed = True
                error_message = str(error)
                error_traceback = traceback.format_exc()

            finally:
                # Close any open nd2 or ims file
                for close_function in close_after_write_functions:
                    close_function()

            # Garbage collect
            gc.collect()

        if conversion_failed:
            logger.print()
            logger.print(f"Failed to convert file: {input_file_path.name}")
            logger.print(f"Error: {error_message}")
            logger.print(error_traceback.rstrip())
            logger.print()

            # Create the report file
            file_conversion.create_single_file_error_report(
                output_folder,
                input_file_path,
                error_message,
                error_traceback,
                logger=logger,
            )
            logger.print("-------------------------------------------------------------------------------------------------------------------------------------------------------------------")

        else:
            # Different prints for different cases
            if image_series is not None and len(image_series) > 1 and output_file_format in (".tif", ".tiff"):
                output_format_name = output_file.suffix.replace(".", "")
                logger.print(
                    f"Saved files to: "
                    f"{output_file.name.removesuffix(output_file.suffix)}_{output_format_name}"
                )

            elif image_series is not None and len(image_series) > 1 and output_file_format == ".ome.zarr":
                logger.print(f"Saved files to: {output_file.name.removesuffix('.ome.zarr')}_omezarr")

            else:
                logger.print(f"Saved File: {output_file.name}")
            logger.print("-------------------------------------------------------------------------------------------------------------------------------------------------------------------")


    ##############################################
    # Helper functions

    def file_choice(logger=None):
        """
        Open a PySide6 dialog to choose a single microscopy file.
        """
        
        # Give the logger
        logger = logger or ConsoleLogger()

        app = QApplication.instance() or QApplication([])

        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Select Microscopy File",
            "",
            "Microscopy files (*.ims *.lif *.ome.tiff *.ome.tif *.tiff *.tif *.nd2 *.zvi *.ics)"
        )

        if not file_path:
            logger.print()
            logger.print("No file selected.")
            return None
        
        return Path(file_path)
    
    #--------------------------------------------------------------------------
    
    def zarr_choice(logger=None):
        """
        Open a PySide6 dialog to choose a single OME-NGFF Zarr file
        """

        # Give the logger
        logger = logger or ConsoleLogger()

        is_it_omezarr = False

        app = QApplication.instance() or QApplication([])

        while is_it_omezarr == False:

            zarr_path = QFileDialog.getExistingDirectory(
                None,
                "Select OME-NGFF Zarr folder",
            )

            if not zarr_path:
                logger.print()
                logger.print("No OME-NGFF Zarr file selected.")
                return None
            
            zarr_path = Path(zarr_path)
            name = zarr_path.name.lower()

            if name.endswith((".ome.zarr", ".zarr")):
                is_it_omezarr = True

            else:
                logger.print()
                logger.print("Selected folder is not an OME-NGFF Zarr.")
                logger.print("Please choose another folder.")

                QApplication.processEvents()

        return zarr_path
    
    #--------------------------------------------------------------------------

        
    def folder_choice(parent=None, logger=None):
        """
        Open a PySide6 dialog to choose a folder and screen it for microscopy files.
        """

        # Give the logger
        logger = logger or ConsoleLogger()

        # Start a bool variable to detect the presence of microscopy files
        are_there_microscopy_files = False

        app = QApplication.instance() or QApplication([])

        # Start a loop for file detection
        while are_there_microscopy_files == False:

            # Open a window to select a folder
            folder_path = QFileDialog.getExistingDirectory(
                parent,
                "Select Folder containing microscopy files",
            )

            # If no folder was selected, simply cancel the conversion
            if not folder_path:
                logger.print()
                logger.print("No folder selected.")
                return [], 0, None

            # Introduce the Path variable
            folder_path = Path(folder_path)

            # Compute the microscopy files that are present
            files = file_conversion.files_from_folder(folder_path)

            # Check if there are actually any microscopy files
            if len(files) != 0:
                are_there_microscopy_files = True
            else:
                logger.print()
                logger.print("No microscopy files found in this folder.", flush=True)
                logger.print("Choose another folder.")

        n_files = len(files)

        return files, n_files, folder_path
    
    #--------------------------------------------------------------------------

    
    def files_from_folder(folder_path):
        """
        Gets all files with the intended file formats that exist in the specified folder.
        """
        
        folder = Path(folder_path)

        # Currently supported: .ims, .ome.zarr, .lif, ome.tiff
        file_extensions = (".ome.tiff", ".ome.tif", ".ims", ".lif", ".tif", ".tiff", ".nd2", ".zvi", ".ics")
        folder_extensions = (".ome.zarr", ".zarr")

        files = []

        for file in folder.iterdir():

            name = file.name.lower()

            if file.is_file() and name.lower().endswith(file_extensions):
                files.append(file)

            elif file.is_dir() and name.endswith(folder_extensions):
                files.append(file)

        return sorted(files)
    
    #--------------------------------------------------------------------------
    
    
    def create_converted_output_folder(input_folder):
        """
        Creates a "Converted Files" folder inside the input folder
        Returns the created output folder path
        """

        input_folder = Path(input_folder)

        output_folder = input_folder / "Converted Files"
        output_folder.mkdir(parents=True, exist_ok=True)

        return output_folder
    

    #--------------------------------------------------------------------------

    
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
            ".ome.tif",
            ".ome.zarr",
            ".tiff",
            ".tif",
            ".ims",
            ".lif",
            ".nd2",
            ".zarr",
            ".zvi",
            ".ics",
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
    

    #--------------------------------------------------------------------------

    
    def get_reader_function(input_file_path):
        """
        Selects the correct function to read the file given its format
        """

        input_file_path = Path(input_file_path)
        input_name = input_file_path.name.lower()

        READER_FUNCTIONS = {
            ".ome.tif": file_reading_functions.read_tifs_as_dask,
            ".ome.tiff": file_reading_functions.read_tifs_as_dask,
            ".ome.zarr": file_reading_functions.read_zarrs_as_dask,
            ".ims": file_reading_functions.read_ims_as_dask,
            ".lif": file_reading_functions.read_lif_as_dask,
            ".zarr": file_reading_functions.read_zarrs_as_dask,
            ".tif": file_reading_functions.read_tifs_as_dask,
            ".tiff": file_reading_functions.read_tifs_as_dask,
            ".nd2": file_reading_functions.read_nd2_as_dask,
            ".zvi": file_reading_functions.read_zvi_as_dask,
            ".ics": file_reading_functions.read_ics_as_dask,

        }

        for input_file_format, reader_function in READER_FUNCTIONS.items():
            if input_name.endswith(input_file_format):
                return reader_function

        raise ValueError(f"Unsupported file format: {input_file_path}")
    

    #--------------------------------------------------------------------------

    
    def get_writer_function(output_file_format):
        """
        Selects the correct function to write the file given the file format that was chosen
        """

        WRITER_FUNCTIONS = {
            ".ome.tiff": writing_functions.write_ome_tiff,
            ".ome.tif":  writing_functions.write_ome_tiff,
            ".ome.zarr": writing_functions.write_ome_zarr,
            ".tif":      writing_functions.write_tiff,
            ".tiff":     writing_functions.write_tiff,
        }

        if output_file_format in WRITER_FUNCTIONS:
                return WRITER_FUNCTIONS[output_file_format]
        
        raise ValueError(f"Unsupported output file format: {output_file_format}")
    

    #--------------------------------------------------------------------------

    
    def create_report(output_folder, n_files, successful_files, failed_files, failed_file_reports, logger=None):
        """
        Creates a report listing the errors for failed files
        """

        # Give the logger
        logger = logger or ConsoleLogger()

        # Immediately leave this function if there are no failed files
        if failed_files == 0:
            return
        
        # Create the report file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_file = Path(output_folder) / f"conversion_report_{timestamp}.txt"

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

        report_path_to_print = report_file.relative_to(Path(output_folder).parent)

        logger.print()
        logger.print(f"Conversion report saved to: {report_path_to_print}")

    #--------------------------------------------------------------------------

    def create_single_file_error_report(output_folder, input_file_path, error_message, error_traceback, logger=None):
        """
        Creates a report that saves the error for a failed single-file conversion
        """

        # Give the logger
        logger = logger or ConsoleLogger()

        # Create the .txt
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_file = Path(output_folder) / f"conversion_error_report_{timestamp}.txt"

        with open(report_file, "w", encoding="utf-8") as report:
            report.write("Single-File Conversion Error Report\n")
            report.write("===================================\n\n")
            report.write(f"File: {input_file_path.name}\n")
            report.write(f"Error: {error_message}\n\n")
            report.write("Traceback:\n")
            report.write("----------\n")
            report.write(error_traceback)

        logger.print()
        logger.print(f"Conversion error report saved to: {report_file}")

    #--------------------------------------------------------------------------

    def get_disk_space(input_file_path):
        """
        Helper function that returns the disk space that a file occupies
        """

        input_file_path = Path(input_file_path)

        # Get the disk space that the file occupies
        if input_file_path.is_file():
            size_bytes = input_file_path.stat().st_size

        # Get the disk space that the folder occupies, in the case of ZARR files
        elif input_file_path.is_dir():
            size_bytes = sum(
                file.stat().st_size
                for file in input_file_path.rglob("*")
                if file.is_file()
            )

        # In case neither of the previous ones worked
        else:
            return "Unknown size"
        
        # Create a list with the relevant memory units
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)

        # Get the correct unit
        for unit in units:
            if size < 1024 or unit == units[-1]:
                break
            size /= 1024

        return f"{size:.2f} {unit}"