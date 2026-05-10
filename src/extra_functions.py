"""
This file has various functions to read data from each file format either as a zarr or a numpy array
"""

#################################################################
# Imports

from __future__ import annotations

from os import PathLike
from pathlib import Path

import zarr
import imaris_ims_file_reader
import tifffile
import dask.array
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

        ims_store = imaris_ims_file_reader.ims(
            str(file_path),
            ResolutionLevelLock=resolution_level,
            aszarr=True,
        )
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
        Open an ome.tiff file as a read-only zarr array and read pixel sizes.
        """

        ometiff_store = tifffile.imread(file_path, aszarr=True)
        img_array = zarr.open(ometiff_store, mode="r")

        img_axes = "".join(img_array.attrs.get("_ARRAY_DIMENSIONS", ""))

        if not img_axes:
            with tifffile.TiffFile(file_path) as tif:
                series = tif.series[0]
                img_axes = series.axes

        with tifffile.TiffFile(file_path) as tif:
            metadata = tifffile.xml2dict(tif.ome_metadata)
            pixels = metadata["OME"]["Image"]["Pixels"]

        pixel_size_metadata = {
            "z": float(pixels.get("PhysicalSizeZ", 1)),
            "y": float(pixels.get("PhysicalSizeY", 1)),
            "x": float(pixels.get("PhysicalSizeX", 1)),
        }

        return img_array, pixel_size_metadata, img_axes
    
    def read_zarr(file_path):
        """
        Opens a zarr and an ome.zarr as a read-only zarr array
        """

        return zarr.open(file_path, mode="r")

class writing_functions:

    def as_dask_array(data):
        """
        Normalize zarr, dask, or numpy input into a dask array.
        """

        if isinstance(data, dask.array.Array):
            return data

        if isinstance(data, zarr.Array):
            return dask.array.from_zarr(data)

        raise TypeError(f"Unsupported array type: {type(data)}")
    
    
    def normalize_to_tczyx(img_array, img_axes):
        """
        Normalize image array to TCZYX order.
        Missing T, C, or Z dimensions are added with size 1.
        """

        img_axes = img_axes.upper()
        img_array = writing_functions.as_dask_array(img_array)

        for dim in "TCZYX":
            if dim not in img_axes:
                axis = "TCZYX".index(dim)
                img_array = dask.array.expand_dims(img_array, axis=axis)
                img_axes = img_axes[:axis] + dim + img_axes[axis:]

        axis_order = [img_axes.index(dim) for dim in "TCZYX"]
        img_array = dask.array.transpose(img_array, axis_order)

        return img_array

    

    def write_ome_zarr(
            output_path,
            img_array,
            img_dims,
            pixel_size_metadata
    ):
        """
        Function that takes a dask array as an input and writes its data into an .ome.zarr file
        """
        
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # If the file that was read has 6 available dimensions, meaning Mosaics + TCZYX
        if len(img_dims) == 6:

            # Get the dimensions
            M, T, C, Z, Y, X = img_dims

        # If there are only 5 dimensions, TCZYX
        else:

            # Get the dimensions
            T, C, Z, Y, X = img_dims

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
            )



    
if __name__ == "__main__":

    print(2)

    input_path = Path(
        r"C:\Users\simao\Desktop\teste\5.2 HIP6 dapi TH DCX 20x_2026-03-25_09.36.31_F04_max_int_proj.ome.tiff"
    )

    if input_path.name.lower().endswith((".ome.tiff", ".ome.tif")):
        output_path = input_path.with_name(Path(input_path.stem).stem + ".ome.zarr")
    else:
        output_path = input_path.with_suffix(".ome.zarr")


    # Reads the ome.tiff
    img_array, pixel_size_metadata, img_axes = file_reading_functions.read_ometiff_as_zarr(input_path)

    # Converts into a dask array
    img_array = writing_functions.as_dask_array(img_array)

    # Normalizes the axes onto TCZYX format
    img_array = writing_functions.normalize_to_tczyx(img_array, img_axes=img_axes)

    print(img_array, pixel_size_metadata, img_array.shape)

    # Write the data into ome.zarr
    writing_functions.write_ome_zarr(
        output_path=output_path,
        img_array=img_array,
        img_dims=img_array.shape,
        pixel_size_metadata=pixel_size_metadata,
    )
