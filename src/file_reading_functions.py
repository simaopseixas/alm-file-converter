"""
This file has various functions to read data from each file format either as a zarr or a numpy array
"""

from __future__ import annotations

from os import PathLike
from pathlib import Path

import zarr
from imaris_ims_file_reader import ims
import tifffile

def files_from_folder(
    folder_path: str | PathLike[str],
):
    folder = Path(folder_path)

    file_extensions = (".ome.tiff", ".ims", ".lif", ".nd2", ".tiff", ".zvi")

    files = []

    for file in folder.iterdir():
        if file.is_file() and file.name.lower().endswith(file_extensions):
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

    ometiff_store = tifffile.imread(file_path, aszarr=True)

    return zarr.open(ometiff_store, mode='r')


    
if __name__ == "__main__":

    repo_root = Path(__file__).resolve().parent.parent
    folder = Path(r"C:\Users\simao\Desktop\teste")
    files = files_from_folder(folder)

    ome_tiff_files = [
        file for file in files
        if file.name.lower().endswith(".ome.tiff")
    ]

    first_ome_tiff = ome_tiff_files[0]

    zarr_array = read_ometiff_as_zarr(first_ome_tiff)

    output_path = first_ome_tiff.with_name(
    first_ome_tiff.name.removesuffix(".ome.tiff") + ".ome.zarr")

    zarr.save_array(str(output_path), zarr_array[:])

    print(first_ome_tiff)

    #zarr_array = read_ometiff_as_zarr(first_ome_tiff)
    

    # print(files)
    
    #ims_files = sorted(ims_folder.glob("*.ims"))

    # for ims_file, i in enumerate(ims_files):
    #     #print(i, ims_file)
    #     zarr_array = read_ims_as_zarr(ims_file)
    #     print(f"{ims_file.name}: {zarr_array.shape}")
