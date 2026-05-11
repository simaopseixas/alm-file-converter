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
import dask
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

from readlif.reader import LifFile

#################################################################
# File Reading Functions

class file_reading_functions:

    def read_ims_as_dask(
        file_path,
        resolution_level=0,
    ):
        """
        Opens an Imaris .ims file as a read-only zarr array.
        Then converts it to a dask array.
        """

        # Read the ims as a zarr
        ims_store = imaris_ims_file_reader.ims(
            str(file_path),
            ResolutionLevelLock=resolution_level,
            aszarr=True,
        )
        img_array = zarr.open(ims_store, mode="r")

        # Converts the zarr to dask
        img_array = writing_functions.as_dask_array(img_array)

        # Get voxel data
        z_size, y_size, x_size = ims_store.ims.resolution

        pixel_size_metadata = {
            "z": z_size,
            "y": y_size,
            "x": x_size,
        }

        img_axes = "TCZYX"

        return img_array, pixel_size_metadata, img_axes


    def read_ometiff_as_dask(file_path):
        """
        Opens an ome.tiff file as a read-only zarr array.
        Then converts it to a dask array.
        """

        # Read the ome.tiff as a zarr
        ometiff_store = tifffile.imread(file_path, aszarr=True)
        zarr_array = zarr.open(ometiff_store, mode="r")

        # Convert the zarr to a dask array
        img_array = writing_functions.as_dask_array(zarr_array)

        # Get the axes of the data
        img_axes = "".join(zarr_array.attrs.get("_ARRAY_DIMENSIONS", ""))

        # Get the voxel metadata
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
    

    
    def read_lif_as_dask(file_path, image_index=0):
        """
        Opens a Leica .lif file.
        Then converts it to a dask array.
        """

        # Define a helper function to build the dask array
        def read_lif_plane(file_path, image_index, z, t, c, m):
            lif = LifFile(file_path)
            img = lif.get_image(image_index)
            return np.asarray(img.get_frame(z=z, t=t, c=c, m=m))

        # Access the lif
        lif = LifFile(file_path)
        img = lif.get_image(image_index)

        # Get the voxel size
        x_size, y_size, z_size, t_scale = img.info["scale"]
        pixel_size_metadata = {
            "z": z_size or 1,
            "y": y_size or 1,
            "x": x_size or 1,
        }

        # Get the dask array
        dims = img.info["dims"]

        M = dims.m
        T = dims.t
        C = len(img.bit_depth)
        Z = dims.z
        Y = dims.y
        X = dims.x
        
        sample = np.asarray(img.get_frame(z=0, t=0, c=0, m=0))
        dtype = sample.dtype

        m_planes = []
        for m in range(M):
            t_planes = []

            for t in range(T):
                c_planes = []

                for c in range(C):
                    z_planes = []

                    for z in range(Z):
                        plane = dask.delayed(read_lif_plane)(file_path, image_index, z, t, c, m)
                        plane = dask.array.from_delayed(plane, shape=(Y,X), dtype=dtype)
                        z_planes.append(plane)

                    c_stack = dask.array.stack(z_planes, axis=0)
                    c_planes.append(c_stack)

                t_stack = dask.array.stack(c_planes, axis=0)
                t_planes.append(t_stack)

            m_stack = dask.array.stack(t_planes, axis=0)
            m_planes.append(m_stack)

        img_array = dask.array.stack(m_planes, axis=0)

        # Get the available axes
        if M > 1:
            img_axes = "MTCZYX"
        else:
            img_array = img_array[0]
            img_axes = "TCZYX"

        return img_array, pixel_size_metadata, img_axes


    def read_omezarr_as_dask(file_path):
        """
        Opens a zarr array in reading.
        Then converts it to a dask array.
        """

        # Access the ome.zarr in reading mode
        sim = ngff_utils.read_sim_from_ome_zarr(file_path, resolution_level=0)
        img_array = sim.data

        # Get the voxel size data
        spacing = si_utils.get_spacing_from_sim(sim)

        pixel_size_metadata = {
            "z": spacing.get("z", 1),
            "y": spacing.get("y", 1),
            "x": spacing.get("x", 1),
        }

        # Get the available axes of the data
        img_axes = "".join(sim.dims).upper()


        return img_array, pixel_size_metadata, img_axes
    
#################################################################
# File Writing Functions

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

        # If it has 6 dimensions, ignore this function, since it doesn't need any normalization
        if img_axes == "MTCZYX":
            return img_array


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
            img_axes,
            pixel_size_metadata
    ):
        """
        Function that takes a dask array as an input and writes its data into an .ome.zarr file
        """
        
        output_path = Path(output_path)
        
        # If the file that was read has 6 available dimensions, meaning Mosaics + TCZYX
        if img_axes == "MTCZYX":

            # Get the dimensions
            M, T, C, Z, Y, X = img_dims

            # Create e new folder for the mosaics to be saved to
            mosaic_folder = output_path.with_name(
                output_path.name.removesuffix(".ome.zarr")
            )

            mosaic_folder.mkdir(parents=True, exist_ok=True)

            for m in range(M):

                if m + 1 > 1:
                    break

                # Change the name of the output mosaic filename
                mosaic_output_path = mosaic_folder / (
                    f"{output_path.name.removesuffix('.ome.zarr')}_mosaic_{m + 1}.ome.zarr"
                )

                sim = si_utils.get_sim_from_array(
                    img_array[m,:,:,:,:,:],
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
                    output_zarr_url=str(mosaic_output_path),
                    overwrite=True,
                    ngff_version="0.4",
                )


        # If there are only 5 dimensions, TCZYX
        else:
            
            # Create simply the 5D file
            output_path.parent.mkdir(parents=True, exist_ok=True)

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