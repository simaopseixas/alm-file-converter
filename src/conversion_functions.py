"""
This file has various functions to read data from each file format either as a zarr or a numpy array
"""

#################################################################
# Imports

from __future__ import annotations

from pathlib import Path

import zarr
import imaris_ims_file_reader
import tifffile
import dask.array
import dask
from multiview_stitcher import spatial_image_utils as si_utils
from multiview_stitcher import ngff_utils
import numpy as np

from readlif.reader import LifFile

import nd2

import contextlib
import os

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

        # Get the closing function
        img_array.close_after_write = ims_store.ims.close

        # Get voxel data
        z_size, y_size, x_size = ims_store.ims.resolution

        pixel_size_metadata = {
            "z": z_size if z_size else None,
            "y": y_size if y_size else None,
            "x": x_size if x_size else None,
        }

        img_axes = "TCZYX"

        return img_array, pixel_size_metadata, img_axes
    
    #--------------------------------------------------------------------------


    def read_tifs_as_dask(file_path):
        """
        Functions that handles .tif, .tiff, .ome.tif and .ome.tiff file formats.
        Opens all of them as a read-only zarr array. Then converts it to a dask array.
        """

        # Read the ome.tiff as a zarr
        tif_store = tifffile.imread(file_path, aszarr=True)
        zarr_array = zarr.open(tif_store, mode="r")

        # Convert the zarr to a dask array
        img_array = writing_functions.as_dask_array(zarr_array)

        # Get the axes of the data
        img_axes = "".join(zarr_array.attrs.get("_ARRAY_DIMENSIONS", ""))

        # Get any metadata
        with tifffile.TiffFile(file_path) as tif:

            # Fallback if there were no axes information available
            if not img_axes:
                series = tif.series[0]
                img_axes = series.axes

            # If there is no OME metadata
            pixel_size_metadata = {
                "z": None, 
                "y": None,
                "x": None,
            }

            # Get OME voxel size metadata
            if tif.ome_metadata:
                metadata = tifffile.xml2dict(tif.ome_metadata)
                pixels = metadata["OME"]["Image"]["Pixels"]

                if pixels.get("PhysicalSizeZ") is not None:
                    pixel_size_metadata["z"] = float(pixels["PhysicalSizeZ"])

                if pixels.get("PhysicalSizeY") is not None:
                    pixel_size_metadata["y"] = float(pixels["PhysicalSizeY"])

                if pixels.get("PhysicalSizeX") is not None:
                    pixel_size_metadata["x"] = float(pixels["PhysicalSizeX"])

            # Get any available voxel size metadata for not OME files
            if not tif.ome_metadata:

                # Get any available ImageJ metadata, if there is any
                imagej_metadata = tif.imagej_metadata or {}

                # Get the Zspacing if it exists
                if imagej_metadata.get("spacing") is not None:
                    pixel_size_metadata["z"] = float(imagej_metadata["spacing"])

                page = tif.pages[0]

                x_resolution = page.tags.get("XResolution")
                y_resolution = page.tags.get("YResolution")
                resolution_unit = page.tags.get("ResolutionUnit")

                if x_resolution is not None and y_resolution is not None:

                    # Get the pixels per unit to then compute the pixel size
                    x_pixels_per_unit = x_resolution.value[0] / x_resolution.value[1]
                    y_pixels_per_unit = y_resolution.value[0] / y_resolution.value[1]

                    # Get the unit used in ImageJ
                    imagej_unit = str(imagej_metadata.get("unit", "")).lower()

                    # Start a dictionary for unit conversions
                    imagej_unit_to_micrometer = {
                        "um": 1.0,
                        "µm": 1.0,
                        "micron": 1.0,
                        "microns": 1.0,
                        "micrometer": 1.0,
                        "micrometers": 1.0,
                        "nm": 0.001,
                        "mm": 1000.0,
                    }

                    # Dictionary for the units that are available in standard tifs
                    unit_to_micrometer = {
                        2: 25400.0, # INCH
                        3: 10000.0, # CENTIMETER
                    }

                    # Start the unit variable
                    unit_size = None

                    # Check if there is actually any unit from ImageJ
                    if imagej_unit in imagej_unit_to_micrometer:
                        unit_size = imagej_unit_to_micrometer[imagej_unit]

                    # If ImageJ gives nothing, get it from the tif directly
                    elif resolution_unit is not None:
                        resolution_unit_value = int(resolution_unit.value)

                        if resolution_unit_value in unit_to_micrometer:
                            unit_size = unit_to_micrometer[resolution_unit_value]

                    # Continue to append pixel size if we got an unit size from any of the two methods
                    if unit_size is not None:

                        if x_pixels_per_unit != 0:
                            pixel_size_metadata["x"] = unit_size / x_pixels_per_unit

                        if y_pixels_per_unit != 0:
                            pixel_size_metadata["y"] = unit_size / y_pixels_per_unit


        return img_array, pixel_size_metadata, img_axes


    #--------------------------------------------------------------------------
    
    def read_lif_as_dask(file_path, image_index=0):
        """
        Opens a Leica .lif file.
        Then converts it to a dask array.
        """

        def read_lif_zstack(file_path, image_index, t, c, m, Z):
            """
            Helper function to access the .lif data to build the dask array
            """
            lif = LifFile(file_path)
            img = lif.get_image(image_index)

            planes = []

            for z in range(Z):
                planes.append(np.asarray(img.get_frame(z=z, t=t, c=c, m=m)))

            return np.stack(planes, axis=0)

        # Access the lif
        lif = LifFile(file_path)
        img = lif.get_image(image_index)

        # Get the voxel size
        x_scale, y_scale, z_scale, t_scale = img.info["scale"]
        pixel_size_metadata = {
            "z": 1 / z_scale if z_scale else None,
            "y": 1 / y_scale if y_scale else None,
            "x": 1 / x_scale if x_scale else None,
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
                    
                    z_stack = dask.delayed(read_lif_zstack)(file_path, image_index, t, c, m, Z)
                    z_stack = dask.array.from_delayed(z_stack, shape=(Z,Y,X), dtype=dtype)
                    c_planes.append(z_stack)

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

    #--------------------------------------------------------------------------

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
    
    #--------------------------------------------------------------------------

    def read_nd2_as_dask(file_path):
        """
        Opens a Nikon .nd2 as a dask array
        """

        # Access the nd2 file
        nd2_file = nd2.ND2File(file_path)

        # Converts the access to dask
        img_array = nd2_file.to_dask()

        # Get the closing file function
        img_array.close_after_write = nd2_file.close

        # Change the axes nomenclature to match the .lif M
        img_axes = "".join(nd2_file.sizes.keys()).upper()        
        img_axes = img_axes.replace("P", "M")
        img_axes = img_axes.replace("V", "M")

        # Get the voxel size from the file
        voxel_size = nd2_file.voxel_size()

        # Convert to metadata dictionary
        pixel_size_metadata = {
            "z": voxel_size.z if voxel_size.z else None,
            "y": voxel_size.y if voxel_size.y else None,
            "x": voxel_size.x if voxel_size.x else None,
        }

        return img_array, pixel_size_metadata, img_axes
    
#################################################################
# File Writing Functions

class writing_functions:
        
    @contextlib.contextmanager
    def suppress_console_output():
        """
        Function to suppress noisy information. Mainly for the .ims reading
        """
        with open(os.devnull, "w") as devnull:
            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                yield

    def as_dask_array(data):
        """
        Normalize zarr, dask, or numpy input into a dask array.
        """

        if isinstance(data, dask.array.Array):
            return data

        if isinstance(data, zarr.Array):
            return dask.array.from_zarr(data)

        raise TypeError(f"Unsupported array type: {type(data)}")
    
    #--------------------------------------------------------------------------
    
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

    #--------------------------------------------------------------------------
    
    def write_ome_zarr(
            output_path,
            img_array,
            img_dims,
            img_axes,
            pixel_size_metadata,
            output_file_format,
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

                # for testing convenience
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

    #--------------------------------------------------------------------------

    def write_ome_tiff(
            output_path,
            img_array,
            img_dims,
            img_axes,
            pixel_size_metadata,
            output_file_format
    ):
        """
        Function that takes a dask array as an input and writes its data into an .ome.tiff file
        """

        # Get the output path
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Verify if the chosen output file format is OME
        output_file_format = output_file_format.lower()
        is_ome_tiff = output_file_format in (".ome.tif", ".ome.tiff")

        def tczyx_plane_access(array, T, C, Z):
            """
            Helper function that accesses (Y,X) data given (T,C) and accessing the Z-stack
            """

            for t in range(T):
                for c in range(C):
                    z_stack = array[t, c, :, :, :].compute()

                    for z in range(Z):
                        yield np.ascontiguousarray(z_stack[z, :, :])

        def get_ome_tiff_metadata(is_ome_tiff):
            """
            Helper function that returns the voxel size metadata if the output image is an OME
            """

            if not is_ome_tiff:
                return None
            
            metadata = { "axes": "TCZYX",}

            if pixel_size_metadata["x"] is not None:
                metadata["PhysicalSizeX"] = pixel_size_metadata["x"]

            if pixel_size_metadata["y"] is not None:
                metadata["PhysicalSizeY"] = pixel_size_metadata["y"]

            if pixel_size_metadata["z"] is not None:
                metadata["PhysicalSizeZ"] = pixel_size_metadata["z"]

            return metadata

        # Initialize the writer
        with tifffile.TiffWriter(output_path, bigtiff=True, ome=is_ome_tiff) as tif:

            # Check the axes of the input file to write accordingly
            if img_axes == "MTCZYX":

                # Get the dimensions
                M, T, C, Z, Y, X = img_dims

                for m in range(M):

                    # for testing convenience
                    if m + 1 > 4:
                        break

                    tif.write(
                        data = tczyx_plane_access(img_array[m, :, :, :, :, :], T, C, Z),
                        shape=(T, C, Z, Y, X),
                        dtype=img_array.dtype,
                        photometric="minisblack",
                        metadata=get_ome_tiff_metadata(is_ome_tiff),
                        compression="zlib",
                        compressionargs={"level": 6},
                        maxworkers=1,
                    )

            else:

                T, C, Z, Y, X = img_dims

                tif.write(
                    data=tczyx_plane_access(img_array, T, C, Z),
                    shape=(T, C, Z, Y, X),
                    dtype=img_array.dtype,
                    photometric="minisblack",
                    metadata=get_ome_tiff_metadata(is_ome_tiff),
                    compression="zlib",
                    compressionargs={"level": 6},
                    maxworkers=1,
                )

# if __name__ == "__main__":

#     path = r"C:\Users\simao\Desktop\Repositories\Microscopy_File_Converter\test-conversions\nd2_and_zvi\Argo_Matrix of Crosses_60X_20260428-1505.nd2"

#     img_array, pixel_size_metadata, img_axes = file_reading_functions.read_nd2_as_dask(path)

#     print(img_array, pixel_size_metadata, img_axes)