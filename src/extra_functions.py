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
        Gets all files with the intended file formats that exist in the specified folder.
        """
        folder = Path(folder_path)

        print("Selected folder:", folder)

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
        img_array = zarr.open(ims_store, mode="r")

        z_size, y_size, x_size = ims_store.ims.resolution

        pixel_size_metadata = {
            "z": z_size,
            "y": y_size,
            "x": x_size,
        }

        return img_array, pixel_size_metadata


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
    
    

import dask.array as da
from multiview_stitcher import spatial_image_utils as si_utils
from multiview_stitcher import (
    fusion,
    io,
    msi_utils,
    vis_utils,
    ngff_utils,
    param_utils,
    registration,
)
import numpy as np

class writing_functions:

    def as_dask_array(data, chunks="auto"):
        """
        Normalize zarr, dask, or numpy input into a dask array.
        """

        if isinstance(data, da.Array):
            return data

        if isinstance(data, zarr.Array):
            return da.from_zarr(data)

        if isinstance(data, np.ndarray):
            return da.from_array(data, chunks=chunks)

        raise TypeError(f"Unsupported array type: {type(data)}")
    

    def write_ome_zarr(
            output_path,
            img_array,
            img_dims,
            pixel_size_metadata
    ):
        
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # If the file that was read has 6 available dimensions, meaning Mosaics + TCZYX
        if len(img_dims) == 6:

            # Get the dimensions
            M, T, C, Z, Y, X = img_dims

            # # If the file is read has having mosaics, but there is only one
            # if M == 1:

            #     msims = []
            #     zarr_paths = []


                
            # # If there are more mosaics
            # else:

            #     msims = []
            #     zarr_paths = []

            #     # Write each tile as an ome.zarr
            #     for itile in range(M):

        # If there are only 5 dimensions, TCZYX
        else:

            # Get the dimensions
            T, C, Z, Y, X = img_dims

            img_array = writing_functions.as_dask_array(img_array)

            sim = si_utils.get_sim_from_array(
                img_array,
                dims = ["t", "c", "z", "y", "x"],
                scale={
                    "z": pixel_size_metadata["z"],
                    "y": pixel_size_metadata["y"],
                    "x": pixel_size_metadata["x"],
                },
                translation={
                    "z": 0,
                    "y": 0,
                    "x": 0,
                },
                transform_key="stage_metadata",
                c_coords=[f"channel_{i}" for i in range(C)],
                t_coords=list(range(T)),
            )
            
            ngff_utils.write_sim_to_ome_zarr(
                sim,
                output_zarr_url=str(output_path),
                overwrite=True,
                ngff_version="0.4",
                zarr_array_creation_kwargs={
                    "chunks": (1, 1, min(10, Z), min(512, Y), min(512, X)),
                },
            )



    
if __name__ == "__main__":

    print(2)

    # repo_root = Path(__file__).resolve().parent.parent
    # folder = Path(r"C:\Users\simao\Desktop\teste")
    # files = file_reading_functions.files_from_folder(folder)

    # print(files)

    # ome_tiff_files = [
    #     file for file in files
    #     if file.name.lower().endswith(".ome.zarr")
    # ]

    # print(ome_tiff_files)

    # first_ome_tiff = ome_tiff_files[0]

    # zarr_array = file_reading_functions.read_zarr(first_ome_tiff)

    # print(zarr_array.shape)
