"""
This file has various functions to read data from each file format either as a zarr or a numpy array
"""

#################################################################
# Imports

from __future__ import annotations

from os import PathLike
from pathlib import Path

import zarr
from imaris_ims_file_reader import ims
import tifffile

#################################################################
# Functions

class file_reading_functions:

    def files_from_folder(
        folder_path: str | PathLike[str],
    ):
        """
        Gets all files with the intende file formats that exist in the specified folder.
        """
        folder = Path(folder_path)

        file_extensions = (".ome.tiff", ".ims", ".lif", ".nd2", ".tiff", ".zvi")
        folder_extensions = (".ome.zarr", ".zarr")

        files = []

        for file in folder.iterdir():

            name = file.name.lower()

            if file.is_file() and name.lower().endswith(file_extensions):
                files.append(file)

            elif file.is_dir() and name.endswith(folder_extensions):
                files.append(file)

        return sorted(files)


    def read_ims_as_zarr(
        file_path,
        resolution_level: int = 0,
    ):
        """
        Open an Imaris .ims file as a read-only zarr array.
        """

        ims_store = ims(str(file_path), ResolutionLevelLock=resolution_level, aszarr=True)
        return zarr.open(ims_store, mode="r")


    def read_ometiff_as_zarr(file_path):
        """
        Open an ome.tiff file as a read-only zarr array.
        """

        ometiff_store = tifffile.imread(file_path, aszarr=True)

        return zarr.open(ometiff_store, mode='r')
    
    def read_zarr(file_path):
        """
        Opens a zarr and an ome.zarr as a read-only zarr array
        """

        return zarr.open(file_path, mode="r")


    
if __name__ == "__main__":

    repo_root = Path(__file__).resolve().parent.parent
    folder = Path(r"C:\Users\simao\Desktop\teste")
    files = file_reading_functions.files_from_folder(folder)

    print(files)

    ome_tiff_files = [
        file for file in files
        if file.name.lower().endswith(".ome.zarr")
    ]

    print(ome_tiff_files)

    first_ome_tiff = ome_tiff_files[0]

    zarr_array = file_reading_functions.read_zarr(first_ome_tiff)

    print(zarr_array.shape)
