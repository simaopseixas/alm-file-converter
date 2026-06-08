"""
This file has various functions to read data from each file format either as a dask array or as a numpy array in the case of .zvi.
Currently supported reading formats:
- .ims, .lif, .nd2, .zvi, .tif, .tiff, .ome.tif, .ome.tiff, .ome.zarr

It also has various functions to write data with various file formats.
Currently supported writing formats:
- .ome.tif, .ome.tiff, .ome.zarr, .tif, .tiff
"""

#################################################################
# Imports

from __future__ import annotations
from pathlib import Path
import zarr
import tifffile
import dask.array
import dask
import numpy as np
from readlif.reader import LifFile
import nd2
import contextlib
import os
from bioio import BioImage
import bioio_bioformats
import ngff_zarr as nz
import h5py

#################################################################
# File Reading Functions

class file_reading_functions:

    #--------------------------------------------------------------------------

    def read_tifs_as_dask(file_path):
        """
        Functions that handles .tif, .tiff, .ome.tif and .ome.tiff file formats.
        Opens the data as a dask array and returns a list of them, as independent image series dictionaries.
        """

        def get_tif_metadata(tif, tif_series, series_index):
            """
            Get voxel size metadata and time frame from OME or Imagej standard TIFF metadata.
            """

            voxel_size_metadata = {
                "z": None, 
                "y": None,
                "x": None,
            }

            ome_image = None
            pixels = None

            #--------------------------------------------------------------------
            # Voxel size

            # Get OME voxel size metadata
            if tif.ome_metadata:
                metadata = tifffile.xml2dict(tif.ome_metadata)
                ome_image = metadata["OME"]["Image"]

                if isinstance(ome_image, list):
                    ome_image = ome_image[series_index]

                pixels = ome_image["Pixels"]

                if pixels.get("PhysicalSizeZ") is not None:
                    voxel_size_metadata["z"] = float(pixels["PhysicalSizeZ"])

                if pixels.get("PhysicalSizeY") is not None:
                    voxel_size_metadata["y"] = float(pixels["PhysicalSizeY"])

                if pixels.get("PhysicalSizeX") is not None:
                    voxel_size_metadata["x"] = float(pixels["PhysicalSizeX"])

            # Get any available voxel size metadata for not OME files with ImageJ standards
            if not tif.ome_metadata:

                # Get any available ImageJ metadata, if there is any
                imagej_metadata = tif.imagej_metadata or {}

                # Get the Zspacing if it exists
                if imagej_metadata.get("spacing") is not None:
                    voxel_size_metadata["z"] = float(imagej_metadata["spacing"])

                page = tif_series.pages[0]

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
                            voxel_size_metadata["x"] = unit_size / x_pixels_per_unit

                        if y_pixels_per_unit != 0:
                            voxel_size_metadata["y"] = unit_size / y_pixels_per_unit

            #--------------------------------------------------------------------
            # Time Frame

            time_metadata = {"t": None}

            # Get OME time metadata
            if pixels is not None:
                if pixels.get("TimeIncrement") is not None:
                    time_metadata["t"] = float(pixels["TimeIncrement"])

            # If OME metadata is not available, get it with the ImageJ standards
            else:
                # Get any available ImageJ metadata, if there is any
                imagej_metadata = tif.imagej_metadata or {}

                # If there is direct time frame interval
                if imagej_metadata.get("finterval") is not None:
                    time_metadata["t"] = float(imagej_metadata["finterval"])

                # If there is an FPS measure
                elif imagej_metadata.get("fps") is not None:
                    fps = float(imagej_metadata["fps"])

                    if fps != 0:
                        time_metadata["t"] = 1 / fps

            #--------------------------------------------------------------------
            # Positional Metadata

            # Start the dictionary
            position_metadata = {
                "x": None,
                "y": None,
                "z": None,
                "unit": "micrometer",
                "extent_min": {
                    "x": None,
                    "y": None,
                    "z": None,
                },
                "extent_max": {
                    "x": None,
                    "y": None,
                    "z": None,
                },
            }

            # Get OME time metadata
            if pixels is not None:

                # Get the available metadata of all 2D YX planes
                plane_metadata = pixels.get("Plane")

                plane_positions = []

                # Normalize the data into a list
                if plane_metadata is not None:
                    if not isinstance(plane_metadata, list):
                        plane_metadata = [plane_metadata]

                    # Get the position of each available YX plane
                    for plane in plane_metadata:
                        plane_position = {
                            "x": float(plane["PositionX"]) if plane.get("PositionX") is not None else None,
                            "y": float(plane["PositionY"]) if plane.get("PositionY") is not None else None,
                            "z": float(plane["PositionZ"]) if plane.get("PositionZ") is not None else None,
                            "unit": "micrometer",
                        }
                        plane_positions.append(plane_position)

                # Store the main value and all the other values on the position_metadata dictionary
                if plane_positions:
                    position_metadata["x"] = plane_positions[0]["x"]
                    position_metadata["y"] = plane_positions[0]["y"]
                    position_metadata["z"] = plane_positions[0]["z"]
                    position_metadata["plane_positions"] = plane_positions

            # If there is no OME metadata
            else:
                # Get any available ImageJ metadata, if there is any
                imagej_metadata = tif.imagej_metadata or {}

                # Get the position metadata
            
                # Here we are solving for the origin:
                # physical_x = (x_pixel - xorigin) * voxel_x <=> physical_x=0 = - xorigin * voxel_x

                if imagej_metadata.get("xorigin") is not None and voxel_size_metadata["x"] is not None:
                    position_metadata["x"] = - float(imagej_metadata["xorigin"]) * voxel_size_metadata["x"]

                if imagej_metadata.get("yorigin") is not None and voxel_size_metadata["y"] is not None:
                    position_metadata["y"] = - float(imagej_metadata["yorigin"]) * voxel_size_metadata["y"]

                if imagej_metadata.get("zorigin") is not None and voxel_size_metadata["z"] is not None:
                    position_metadata["z"] = - float(imagej_metadata["zorigin"]) * voxel_size_metadata["z"]

            return voxel_size_metadata, time_metadata, position_metadata
    
        def read_tif_series_as_dask(file_path, seriex_index, tif_series):
            """
            Read a single OME-TIFF series as a dask array.
            Returns the dask array and its axes
            """

            # Read the ome.tiff as a zarr
            tif_store = tifffile.imread(file_path, aszarr=True, series=seriex_index)
            zarr_array = zarr.open(tif_store, mode="r")

            # Convert the zarr to a dask array
            img_array = writing_functions.as_dask_array(zarr_array)

            # Get the axes of the data
            img_axes = "".join(zarr_array.attrs.get("_ARRAY_DIMENSIONS", ""))

            # Fallback if no axes were registered before
            if not img_axes:
                img_axes = tif_series.axes

            return img_array, img_axes
        
        image_series = []

        # Open the tif file
        with tifffile.TiffFile(file_path) as tif:

            # Get the data from each series
            for series_index, tif_series in enumerate(tif.series):
                img_array, img_axes = read_tif_series_as_dask(file_path, series_index, tif_series)

                # Get the metadata of the series
                voxel_size_metadata, time_metadata, position_metadata = get_tif_metadata(tif, tif_series, series_index)

                # Append the information onto the dictionary
                image_series.append({
                    "array": img_array,
                    "axes": img_axes,
                    "voxel_size_metadata": voxel_size_metadata,
                    "time_metadata": time_metadata,
                    "position_metadata": position_metadata
                })

        if not image_series:
            raise ValueError(f"No readable image series found in file: {file_path}")
        
        return image_series
    

    #--------------------------------------------------------------------------

    def read_zarrs_as_dask(file_path):
        """
        Opens an OME-NGFF Zarr stored in a .zarr or .ome.zarr folder.
        Then converts it to a dask array and appends it to a dictionary with the image series
        """

        def get_zarr_metadata(ngff_image):
            """
            Helper function that gets the voxel size and the time frame metadata
            """

            def position_to_micrometers(position, unit):
                """
                Function that converts a zarr position to micrometers
                """
                if position is None or unit is None:
                    return None

                unit_to_micrometer = {
                    "meter": 1_000_000,
                    "centimeter": 10_000,
                    "millimeter": 1_000,
                    "micrometer": 1,
                    "nanometer": 0.001,
                    "angstrom": 0.0001,
                }

                unit_factor = unit_to_micrometer.get(unit)

                if unit_factor is None:
                    return None

                return float(position) * unit_factor
            
            # Get the scale dictionary from the data
            scale = ngff_image.scale or {}

            #-----------------------------------------------
            # Get the voxel size
            voxel_size_metadata = {
                "z": scale.get("z", None),
                "y": scale.get("y", None),
                "x": scale.get("x", None),
            }

            #-----------------------------------------------
            # Get the time frame
            time_metadata = {"t": scale.get("t", None)}

            #-----------------------------------------------
            # Get the position metadata

            # get the spatial translation and axis units
            translation = ngff_image.translation or {}
            axes_units = ngff_image.axes_units or {}

            # get the positions
            position_x = position_to_micrometers(translation.get("x"), axes_units.get("x"))
            position_y = position_to_micrometers(translation.get("y"), axes_units.get("y"))
            position_z = position_to_micrometers(translation.get("z"), axes_units.get("z"))

            # append the positions to the dictionary
            position_metadata = {
                "x": position_x,
                "y": position_y,
                "z": position_z,
                "unit": "micrometer",
                "extent_min": {
                    "x": position_x,
                    "y": position_y,
                    "z": position_z,
                },
                "extent_max": {
                    "x": None,
                    "y": None,
                    "z": None,
                },
            }


            return voxel_size_metadata, time_metadata, position_metadata
        
        # Access the dask image
        multiscales = nz.from_ngff_zarr(str(file_path))

        # Access the full resolution image
        image = multiscales.images[0]

        # Convert the dask array
        img_array = image.data
        img_axes = "".join(image.dims).upper()

        # Raises an error if it has more than 5D
        if img_array.ndim > 5:
            raise ValueError(
                f"OME-Zarr data must be 2D to 5D. Got {img_array.ndim}D with axes {img_axes}."
            )
        
        # Get the metadata
        voxel_size_metadata, time_metadata, position_metadata = get_zarr_metadata(image)

        image_series = [{
            "array": img_array,
            "axes": img_axes,
            "voxel_size_metadata": voxel_size_metadata,
            "time_metadata": time_metadata,
            "position_metadata": position_metadata,
        }]

        return image_series
    
    
    #--------------------------------------------------------------------------
    
    def read_ims_as_dask(file_path, resolution_level=0):
        """
        Opens an Imaris .ims file with HDF5 and converts it into a dask array.
        Returns the data as a list with a dictionary.
        """

        def get_attr_text(value):
            """
            Helper function that converts an HDF5 attribute into simple text
            """

            # Convert the value into an array
            value = np.asarray(value)

            # Check if the array contains byte strings
            if value.dtype.kind == "S":
                # If it does, convert the data to a simple string
                return b"".join(value.tolist()).decode("utf-8", errors="ignore")
            
            else:
                return str(value)
            
        def get_attr_float(group, name):
            """
            Helper function that converts an HDF5 attribute into a float value
            """
            return float(get_attr_text(group.attrs[name]))
        
        def get_attr_int(group, name):
            """
            Helper function that converets an HDF5 attribute into an integer value
            """
            return int(float(get_attr_text(group.attrs[name])))
        
        def get_ims_metadata(ims_file, img_array):
            """
            Helper function that gets the voxel size and the time frame metadata
            """

            #-----------------------------------------------------------------------------
            # Voxel size

            # Get the image available metadata
            image_info = ims_file["DataSetInfo"]["Image"]

            # Retrieve the image's extents, to calculate the voxel size
            x_extent = get_attr_float(image_info, "ExtMax0") - get_attr_float(image_info, "ExtMin0")
            y_extent = get_attr_float(image_info, "ExtMax1") - get_attr_float(image_info, "ExtMin1")
            z_extent = get_attr_float(image_info, "ExtMax2") - get_attr_float(image_info, "ExtMin2")

            # Get the data shape
            T, C, Z, Y, X = img_array.shape

            # Calculate the voxel size
            voxel_size_metadata = {
                "z": z_extent / Z if Z > 1 else None,
                "y": y_extent / Y if Y > 1 else None,
                "x": x_extent / X if X > 1 else None,
            }

            #-----------------------------------------------------------------------------
            # Time frame

            # Fill the time data as None
            time_metadata = {"t": None}

            #-----------------------------------------------------------------------------
            # Positional metadata

            # Get the images minimum and maximum extent
            ext_min_x = get_attr_float(image_info, "ExtMin0")
            ext_min_y = get_attr_float(image_info, "ExtMin1")
            ext_min_z = get_attr_float(image_info, "ExtMin2")

            ext_max_x = get_attr_float(image_info, "ExtMax0")
            ext_max_y = get_attr_float(image_info, "ExtMax1")
            ext_max_z = get_attr_float(image_info, "ExtMax2")

            # Retrieve extent information into a dictionary
            position_metadata = {
                "x": ext_min_x,
                "y": ext_min_y,
                "z": ext_min_z,
                "unit": "micrometer",
                "extent_min": {
                    "x": ext_min_x,
                    "y": ext_min_y,
                    "z": ext_min_z,
                },
                "extent_max": {
                    "x": ext_max_x,
                    "y": ext_max_y,
                    "z": ext_max_z,
                },
            }

            return voxel_size_metadata, time_metadata, position_metadata
        
        # Read the ims
        ims_file = h5py.File(file_path, "r")

        # Choose the resolution level
        resolution_group = ims_file["DataSet"][f"ResolutionLevel {resolution_level}"]

        # Get the available timepoints
        timepoint_names = sorted(
            resolution_group.keys(),
            key=lambda name: int(name.split()[-1]),
        )

        # Get the available channels
        channel_names = sorted(
            resolution_group[timepoint_names[0]].keys(),
            key=lambda name: int(name.split()[-1]),
        )

        # Create the final dask array that goes into the dictionary
        t_stacks = []
        for timepoint_name in timepoint_names:
            c_stacks = []

            for channel_name in channel_names:
                channel_group = resolution_group[timepoint_name][channel_name]
                c_stack = channel_group["Data"]

                z_size = get_attr_int(channel_group, "ImageSizeZ")
                y_size = get_attr_int(channel_group, "ImageSizeY")
                x_size = get_attr_int(channel_group, "ImageSizeX")

                c_stack = dask.array.from_array(c_stack, c_stack.chunks)[:z_size, :y_size, :x_size]

                # Create the CZYX dataset
                c_stacks.append(c_stack)

            # Create the TCZYX dataset
            t_stack = dask.array.stack(c_stacks, axis=0)
            t_stacks.append(t_stack)

        # Create the final dataset
        img_array = dask.array.stack(t_stacks, axis=0)

        # Get the dataset metadata
        voxel_size_metadata, time_metadata, position_metadata = get_ims_metadata(ims_file, img_array)

        image_series = [{
            "array": img_array,
            "axes": "TCZYX",
            "voxel_size_metadata": voxel_size_metadata,
            "time_metadata": time_metadata,
            "position_metadata": position_metadata,
            "file_close_function": ims_file.close
        }]

        return image_series    

    #--------------------------------------------------------------------------

    def read_lif_as_dask(file_path):
        """
        Opens a Leica .lif file.
        Returns a list of independent 5D TCZYX image series dictionaries
        with the series dask array, axes and voxel size data.
        """

        def get_lif_metadata(lif, img, m):
            """
            Helper function that gets the voxel size, time frame and positional metadata of a single series from a Leica .lif
            """

            #---------------------------------------------------------------------------
            # Voxel size

            # Get the voxel size metadata
            x_scale, y_scale, z_scale, t_scale = img.info["scale"]
            voxel_size_metadata = {
                "z": 1 / z_scale if z_scale else None,
                "y": 1 / y_scale if y_scale else None,
                "x": 1 / x_scale if x_scale else None,
            }

            #---------------------------------------------------------------------------
            # Time frame

            time_metadata = {"t": 1 / t_scale if t_scale else None} # in seconds

            #---------------------------------------------------------------------------
            # Position metadata

            position_metadata = {
                "x": None,
                "y": None,
                "z": None,
                "unit": "micrometer",
                "extent_min": {
                    "x": None,
                    "y": None,
                    "z": None,
                },
                "extent_max": {
                    "x": None,
                    "y": None,
                    "z": None,
                },
            }

            # Initialize the necessary objects
            tile_positions = []
            stage_position = None
            extent_size = {
                "x": None,
                "y": None,
                "z": None,
            }

            # Scan the XML file
            for element in lif.xml_root.iter():

                # Skip anything that is not identified as an "Element"
                if not element.tag.endswith("Element"):
                    continue

                # Check if said Element corresponds to the lif image series we want
                if element.attrib.get("Name") != img.info["name"]:
                    continue

                #
                for metadata_element in element.iter():

                    # If the series is a mosaic / tile position
                    if metadata_element.tag.endswith("Tile"):
                        tile_positions.append({
                            "y": float(metadata_element.attrib["PosY"]) * 1e6 if metadata_element.attrib.get("PosY") is not None else None,
                            "z": float(metadata_element.attrib["PosZ"]) * 1e6 if metadata_element.attrib.get("PosZ") is not None else None,
                            "x": float(metadata_element.attrib["PosX"]) * 1e6 if metadata_element.attrib.get("PosX") is not None else None,
                            "field_x": int(metadata_element.attrib["FieldX"]) if metadata_element.attrib.get("FieldX") is not None else None,
                            "field_y": int(metadata_element.attrib["FieldY"]) if metadata_element.attrib.get("FieldY") is not None else None,
                        })

                    # If the series is a simple single-series
                    elif metadata_element.tag.endswith("ATLCameraSettingDefinition"):
                        stage_position = {
                            "x": float(metadata_element.attrib["StagePosX"]) * 1e6 if metadata_element.attrib.get("StagePosX") is not None else None,
                            "y": float(metadata_element.attrib["StagePosY"]) * 1e6 if metadata_element.attrib.get("StagePosY") is not None else None,
                            "z": float(metadata_element.attrib["ZPosition"]) * 1e6 if metadata_element.attrib.get("ZPosition") is not None else None,
                        }

                    # Also get the Estent metadata for each of the previous options
                    elif metadata_element.tag.endswith("DimensionDescription"):

                        dim_id = metadata_element.attrib.get("DimID")
                        length = metadata_element.attrib.get("Length")
                        unit = metadata_element.attrib.get("Unit")

                        if length is None:
                            continue

                        unit_to_micrometer = {
                            "m": 1000000,
                            "meter": 1000000,
                            "meters": 1000000,
                            "mm": 1000,
                            "millimeter": 1000,
                            "millimeters": 1000,
                            "um": 1,
                            "µm": 1,
                            "micrometer": 1,
                            "micrometers": 1,
                            "nm": 0.001,
                            "nanometer": 0.001,
                            "nanometers": 0.001,
                        }

                        length = float(length)

                        unit = (metadata_element.attrib.get("Unit") or "").lower()
                        unit_factor = unit_to_micrometer.get(unit)

                        if unit_factor is not None:
                            length *= unit_factor
                        else:
                            length = None

                        if dim_id == "1":
                            extent_size["x"] = length

                        if dim_id == "2":
                            extent_size["y"] = length

                        if dim_id == "3":
                            extent_size["z"] = length

                break

            # If there are several tile positions, get the correct tile
            if m < len(tile_positions):
                tile_position = tile_positions[m]

                # Append the metadata
                position_metadata["x"] = tile_position["x"]
                position_metadata["y"] = tile_position["y"]
                position_metadata["z"] = tile_position["z"]
                position_metadata["field_x"] = tile_position["field_x"]
                position_metadata["field_y"] = tile_position["field_y"]

            # If its a simple-series
            elif stage_position is not None:
                position_metadata["x"] = stage_position["x"]
                position_metadata["y"] = stage_position["y"]
                position_metadata["z"] = stage_position["z"]

            # Append the min. extent metadata
            position_metadata["extent_min"] = {
                "x": position_metadata["x"],
                "y": position_metadata["y"],
                "z": position_metadata["z"],
            }

            # Append the max. extent metadata
            for axis in ["x", "y", "z"]:
                if position_metadata[axis] is not None and extent_size[axis] is not None:
                    position_metadata["extent_max"][axis] = position_metadata[axis] + extent_size[axis]
                else:
                    position_metadata["extent_max"][axis] = None


            return voxel_size_metadata, time_metadata, position_metadata
        

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
        
        def build_tczyx_array(file_path, image_index, img, m):
            """
            Helper function that constructs the TCZYX dask array inside a single .lif series
            """

            # Get the dimensions
            dims = img.info["dims"]

            T = dims.t
            C = len(img.bit_depth)
            Z = dims.z
            Y = dims.y
            X = dims.x

            sample = np.asarray(img.get_frame(z=0, t=0, c=0, m=m))
            dtype = sample.dtype

            t_planes = []
            for t in range(T):
                c_planes = []

                for c in range(C):

                    z_stack = dask.delayed(read_lif_zstack)(file_path, image_index, t, c, m, Z)
                    z_stack = dask.array.from_delayed(z_stack, shape=(Z,Y,X), dtype=dtype)
                    c_planes.append(z_stack)

                c_stack = dask.array.stack(c_planes, axis=0)
                t_planes.append(c_stack)

            t_stack = dask.array.stack(t_planes, axis=0)

            return t_stack
        
        # Access the lif
        lif = LifFile(file_path)

        # Extract the series
        images = list(lif.get_iter_image())

        if not images:
            raise ValueError(f"No readable image series found in .lif file: {file_path}")
        
        image_series = []

        for image_index, img in enumerate(images):
            
            # Get the series dimensions
            dims = img.info["dims"]

            # Get the available mosaics
            M = dims.m

            # For each mosaic inside the "series"
            for m in range(M):

                # Get the metadata
                voxel_size_metadata, time_metadata, position_metadata = get_lif_metadata(lif, img, m)

                # Compute the TCZYX dask array
                image_array = build_tczyx_array(file_path, image_index, img, m)

                # Append the mosaic information on the list
                image_series.append({
                    "array": image_array,
                    "axes": "TCZYX",
                    "voxel_size_metadata": voxel_size_metadata,
                    "time_metadata": time_metadata,
                    "position_metadata": position_metadata,
                })

        return image_series

    
    #--------------------------------------------------------------------------

    def read_nd2_as_dask(file_path):
        """
        Opens a Nikon .nd2 file as a dask array and returns a list of image series dictionaries
        """

        def get_nd2_metadata(nd2_file, series_index=None):
            """
            Helper function that gets the voxel size and time frame
            """

            #------------------------------------------------------
            # Voxel size

            voxel_size = nd2_file.voxel_size()

            # Get the metadata dictionary
            voxel_size_metadata = {
                "z": voxel_size.z if voxel_size.z else None,
                "y": voxel_size.y if voxel_size.y else None,
                "x": voxel_size.x if voxel_size.x else None,
            }

            #------------------------------------------------------
            # Time Frame

            time_metadata = {"t": None}

            for loop in nd2_file.experiment:

                # See if there is an available TimeLoop in the file
                if getattr(loop, "type", None) == "TimeLoop":
                    # Get the TimeLoop parameters
                    parameters = getattr(loop, "parameters", None)

                    if parameters is None:
                        continue

                    # Get the periodMs parameter
                    period_ms = getattr(parameters, "periodMs", None)

                    # If periodMs exists, append it to the time frame metadata
                    if period_ms is not None and period_ms > 0:
                        time_metadata["t"] = period_ms / 1000
                        break

                    # If periodMs doesn't exist, try periodDiff
                    period_diff = getattr(parameters, "periodDiff", None)
                    avg_ms = getattr(period_diff, "avg", None) if period_diff is not None else None

                    # If periodDiff exists, append it to the time frame metadata
                    if avg_ms is not None and avg_ms > 0:
                        time_metadata["t"] = avg_ms / 1000
                        break

            #------------------------------------------------------
            # Position Metadata

            position_metadata = {
                "x": None,
                "y": None,
                "z": None,
                "unit": "micrometer",
                "extent_min": {
                    "x": None,
                    "y": None,
                    "z": None,
                },
                "extent_max": {
                    "x": None,
                    "y": None,
                    "z": None,
                },
            }

            # use the first position when the .nd2 contains only one image series
            position_index = series_index if series_index is not None else 0
            sequence_index = None

            # find the first frame that belongs to the requested position
            for frame_index, loop_index in enumerate(nd2_file.loop_indices):
                frame_position_index = loop_index.get("P", loop_index.get("V", 0))

                if frame_position_index == position_index:
                    sequence_index = frame_index
                    break

            # read the positional metadata from the selected frame
            if sequence_index is not None:
                frame_metadata = nd2_file.frame_metadata(sequence_index)
                channels = getattr(frame_metadata, "channels", [])

                # stage positions are shared between channels
                # use the first available channel
                if channels:
                    position = getattr(channels[0], "position", None)
                    stage_position = getattr(position, "stagePositionUm", None)

                    # no need for conversion, since .nd2 positions are already in micrometers
                    if stage_position is not None:
                        position_metadata["x"] = float(stage_position.x)
                        position_metadata["y"] = float(stage_position.y)
                        position_metadata["z"] = float(stage_position.z)

                        position_metadata["extent_min"] = {
                            "x": position_metadata["x"],
                            "y": position_metadata["y"],
                            "z": position_metadata["z"],
                        }

            return voxel_size_metadata, time_metadata, position_metadata
        

        # Access the nd2 file
        nd2_file = nd2.ND2File(file_path)

        # Converts the access to dask
        img_array = nd2_file.to_dask()

        # Get the axes
        img_axes = "".join(nd2_file.sizes.keys()).upper()

        # Detect ND2 position/view axis
        position_axis_name = None

        if "P" in img_axes:
            position_axis_name = "P"

        elif "V" in img_axes:
            position_axis_name = "V"

        image_series = []

        # If there are indeed different positions/views
        if position_axis_name is not None:

            position_axis = img_axes.index(position_axis_name)
            n_positions = img_array.shape[position_axis]
            series_axes = img_axes.replace(position_axis_name, "")

            for p in range(n_positions):

                # Get the series metadata
                voxel_size_metadata, time_metadata, position_metadata = get_nd2_metadata(nd2_file, series_index=p)

                image_array = dask.array.take(img_array, p, axis=position_axis)
                image_series.append({
                    "array": image_array,
                    "axes": series_axes,
                    "voxel_size_metadata": voxel_size_metadata,
                    "time_metadata": time_metadata,
                    "position_metadata": position_metadata,
                })

                # Append the closing function in the final position
                if p == n_positions - 1:
                    image_series[-1]["file_close_function"] = nd2_file.close

        # If there is only one series
        else:
            
            # Get the single series metadata
            voxel_size_metadata, time_metadata, position_metadata = get_nd2_metadata(nd2_file, series_index=0)

            image_series.append({
                "array": img_array,
                "axes": img_axes,
                "voxel_size_metadata": voxel_size_metadata,
                "time_metadata": time_metadata,
                "position_metadata": position_metadata,
                "file_close_function": nd2_file.close   # closing function to be used during conversion
            })


        return image_series

    
    #--------------------------------------------------------------------------

    def read_zvi_as_dask(file_path):
        """
        Opens a Zeiss .zvi as a dask array.
        This function doesn't function lazily. Since .zvi doesn't support lazy reading, 
        the whole dataset is loaded into memory as a numpy array and converted to dask.
        Then the function returns a dictionary with the dataset and metadata
        """

        def get_zvi_metadata(zvi_img):
            """
            Helper function that gets the voxel size and time frame metadata
            """

            def position_to_micrometers(position, unit):
                """
                Function that converts the position from the zvi to micrometers
                """

                if position is None or unit is None:
                    return None

                unit_to_micrometer = {
                    "m": 1_000_000,
                    "cm": 10_000,
                    "mm": 1_000,
                    "µm": 1,
                    "nm": 0.001,
                }

                unit_factor = unit_to_micrometer.get(unit.value)

                if unit_factor is None:
                    return None

                return float(position) * unit_factor

            #-------------------------------------------------------------
            # Get voxel size metadata, if accessible through BioIO
            voxel_sizes = zvi_img.physical_pixel_sizes

            voxel_size_metadata = {
                "z": voxel_sizes.Z,
                "y": voxel_sizes.Y,
                "x": voxel_sizes.X
            }

            #-------------------------------------------------------------
            # Get time metadata, if accessible through BioIO
            time_metadata = {"t": zvi_img.time_interval if zvi_img.time_interval else None}

            #-------------------------------------------------------------
            # Get positional metadata

            position_metadata = {
                "x": None,
                "y": None,
                "z": None,
                "unit": "micrometer",
                "extent_min": {
                    "x": None,
                    "y": None,
                    "z": None,
                },
                "extent_max": {
                    "x": None,
                    "y": None,
                    "z": None,
                },
            }

            # Access the OME metadata
            ome_metadata = zvi_img.ome_metadata
            scene_index = zvi_img.current_scene_index

            if scene_index < len(ome_metadata.images):
                pixels = ome_metadata.images[scene_index].pixels
                plane_positions = []

                # Get the plane positions for each available plane
                for plane in pixels.planes:
                    plane_positions.append({
                        "x": position_to_micrometers(
                            plane.position_x,
                            plane.position_x_unit,
                        ),
                        "y": position_to_micrometers(
                            plane.position_y,
                            plane.position_y_unit,
                        ),
                        "z": position_to_micrometers(
                            plane.position_z,
                            plane.position_z_unit,
                        ),
                        "unit": "micrometer",
                    })

                # Check if the planes actually have positions
                has_plane_positions = False

                for plane_position in plane_positions:
                    if (
                        plane_position.get("x") is not None
                        or plane_position.get("y") is not None
                        or plane_position.get("z") is not None
                    ):
                        has_plane_positions = True
                        break

                # If there are plane positions, append them to the dictionary
                if has_plane_positions:
                    position_metadata["plane_positions"] = plane_positions
                    position_metadata["x"] = plane_positions[0]["x"]
                    position_metadata["y"] = plane_positions[0]["y"]
                    position_metadata["z"] = plane_positions[0]["z"]

                    position_metadata["extent_min"] = {
                        "x": position_metadata["x"],
                        "y": position_metadata["y"],
                        "z": position_metadata["z"],
                    }

            return voxel_size_metadata, time_metadata, position_metadata


        # Access the .zvi file
        img = BioImage(file_path, reader=bioio_bioformats.Reader)

        # Get the data into numpy
        img_array = img.get_image_data("TCZYX")

        # Get the metadata
        voxel_size_metadata, time_metadata, position_metadata = get_zvi_metadata(img)

        # Convert the numpy array to dask, to make it compatible with the conversion pipeline
        img_array = dask.array.from_array(
            img_array,
            chunks=(1,1,1,img_array.shape[-2],img_array.shape[-1])
        )

        image_series = [{
            "array": img_array,
            "axes": "TCZYX",
            "voxel_size_metadata": voxel_size_metadata,
            "time_metadata": time_metadata,
            "position_metadata": position_metadata,
        }]


        return image_series
    
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
        Normalize image array to TCZYX or MTCZYX order.
        Missing T, C, or Z dimensions are added with size 1.
        If an M dimension is present, it is preserved as the leading axis.
        """

        # Normalize the axis string and make sure the array is dask-backed
        img_axes = img_axes.upper()
        img_array = writing_functions.as_dask_array(img_array)

        # This function expects positions/mosaics to already be separate series
        if "M" in img_axes:
            raise ValueError(
                "M dimensions must be split into separate image series before normalization."
            )

        target_axes = "TCZYX"

        # If there is already a match do not change anything
        if img_axes == target_axes:
            return img_array, target_axes

        # Add any missing dimensions in their final target positions
        for dim in target_axes:
            if dim not in img_axes:
                axis = target_axes.index(dim)
                img_array = dask.array.expand_dims(img_array, axis=axis)
                img_axes = img_axes[:axis] + dim + img_axes[axis:]

        # Reorder the existing dimensions into TCZYX
        axis_order = [img_axes.index(dim) for dim in target_axes]
        img_array = dask.array.transpose(img_array, axis_order)

        return img_array, target_axes

    #--------------------------------------------------------------------------

    def write_ome_zarr(output_path, image_series):
        """
        Function that takes a list of dictionaries with image series data as an input
        and writes it into an .ome.zarr file
        """

        def get_scale(voxel_size_metadata, time_metadata):
            """
            Helper function that returns the voxel size and time metadata for the OME-ZARR writing
            """

            # Compute the scales dictionary
            scale = {
                "t": time_metadata["t"] if time_metadata["t"] is not None else 1,
                "z": voxel_size_metadata["z"] if voxel_size_metadata["z"] is not None else 1,
                "y": voxel_size_metadata["y"] if voxel_size_metadata["y"] is not None else 1,
                "x": voxel_size_metadata["x"] if voxel_size_metadata["x"] is not None else 1,
            }

            return scale
        
        def get_translation(position_metadata):
            """
            Helper function that gets the position metadata as a translation for the 5D TCZYX stack
            """

            # Compute the translation dictionary
            translation = {
                "z": position_metadata["z"] if position_metadata.get("z") is not None else 0,
                "y": position_metadata["y"] if position_metadata.get("y") is not None else 0,
                "x": position_metadata["x"] if position_metadata.get("x") is not None else 0,
            }

            return translation
        
        def write_single_ome_zarr(series_output_path, series):
            """
            Helper function that writes a single 5D OME-ZARR file
            """

            # Get the series data
            img_array = series["array"]
            img_axes = series["axes"]
            voxel_size_metadata = series["voxel_size_metadata"]
            time_metadata = series["time_metadata"]
            position_metadata = series["position_metadata"]

            # Raise an error if the axes are not TCZYX
            if img_axes != "TCZYX":
                raise ValueError(f"The series must be TCZYX before writing. Got {img_axes}")
            
            # Create an ngff image
            ngff_image = nz.to_ngff_image(
                img_array,
                dims=["t", "c", "z", "y", "x"],
                scale=get_scale(voxel_size_metadata, time_metadata),
                translation=get_translation(position_metadata),
                axes_units={
                    "t": "second",
                    "z": "micrometer",
                    "y": "micrometer",
                    "x": "micrometer",
                },
                name="image")

            # Create the multiscales for pyramids
            multiscales = nz.to_multiscales(
                ngff_image,
                scale_factors=[
                    {"z": 1, "y": 2, "x": 2},
                    {"z": 1, "y": 4, "x": 4},
                    {"z": 1, "y": 8, "x": 8},
                    {"z": 1, "y": 16, "x": 16},
                    {"z": 1, "y": 32, "x": 32},
                ],
                method=nz.Methods.DASK_IMAGE_NEAREST,
                cache=False,)
            
            # Write the OME-Zarr file
            nz.to_ngff_zarr(
                str(series_output_path),
                multiscales,
                version="0.4",
                overwrite=True,
                compressor=None,
            )

        # Get the output path
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # If there is a single series
        if len(image_series) == 1:
            write_single_ome_zarr(output_path, image_series[0])

        # If there is more than one series in the list
        else:

            # Create the folder in which the series will be saved
            output_format_name = ".ome.zarr".replace(".", "").upper()

            series_folder = output_path.with_name(
                f"{output_path.name.removesuffix('.ome.zarr')}_{output_format_name}")
            
            series_folder.mkdir(parents=True, exist_ok=True)

            # Write a file for each of the available series
            for series_index, series in enumerate(image_series, start=1):
                series_output_path = series_folder / (f"series_{series_index}.ome.zarr" )

                write_single_ome_zarr(series_output_path, series)


    #--------------------------------------------------------------------------


    def write_ome_tiff(output_path, image_series):
        """
        Function that takes a list of dask arrays as an input and writes its data into an .ome.tif or .ome.tiff file
        """

        def get_ome_metadata(voxel_size_metadata, time_metadata, position_metadata, T, C, Z):
            """
            Helper function that computes an OME voxel size dictionary for metadata
            """

            # Create the OME metadata dictionary
            ome_metadata = { "axes": "TCZYX"}

            #----------------------------------------------------------------
            # Voxel size
            if voxel_size_metadata["x"] is not None:
                ome_metadata["PhysicalSizeX"] = voxel_size_metadata["x"]

            if voxel_size_metadata["y"] is not None:
                ome_metadata["PhysicalSizeY"] = voxel_size_metadata["y"]

            if voxel_size_metadata["z"] is not None:
                ome_metadata["PhysicalSizeZ"] = voxel_size_metadata["z"]

            #----------------------------------------------------------------
            # Time metadata

            if time_metadata["t"] is not None:
                ome_metadata["TimeIncrement"] = time_metadata["t"]
                ome_metadata["TimeIncrementUnit"] = "s"

            #----------------------------------------------------------------
            # Position metadata

            plane_metadata = []

            # Get the X, Y, Z min. extents
            extent_min = position_metadata.get("extent_min", {})
            # Get the X, Y, Z max. extents
            extent_max = position_metadata.get("extent_max", {})
            # Get any available plane positions
            plane_positions = position_metadata.get("plane_positions", [])
            plane_index = 0

            # Get any available volume positions
            position_x = position_metadata.get("x")
            position_y = position_metadata.get("y")
            position_z = position_metadata.get("z")

            # Get any available XYZ extents
            z_min = extent_min.get("z")
            z_max = extent_max.get("z")
            z_step = voxel_size_metadata.get("z")

            # Calculate the zstep if was not read
            if z_step is None:
                if z_min is not None and z_max is not None and Z > 1:
                    z_step = (z_max - z_min) / (Z - 1)

            # Write the positions of each plane
            for t in range(T):
                for c in range(C):
                    for z in range(Z):

                        plane = {}

                        # get the plane position if available
                        if plane_index < len(plane_positions):
                            plane_position = plane_positions[plane_index]
                        else:
                            plane_position = {}

                        plane_x = plane_position.get("x")
                        plane_y = plane_position.get("y")
                        plane_z = plane_position.get("z")

                        if plane_x is None:
                            plane_x = position_x
                        if plane_y is None:
                            plane_y = position_y
                        
                        # either get the plane position or calculate it
                        if plane_z is None:
                            if z_min is not None and z_step is not None:
                                plane_z = z_min + z * z_step
                            elif position_z is not None and z_step is not None:
                                plane_z = position_z + z * z_step
                            else:
                                plane_z = position_z

                        # finally, append the value to the metadata
                        if plane_x is not None:
                            plane["PositionX"] = plane_x
                            plane["PositionXUnit"] = "µm"

                        if plane_y is not None:
                            plane["PositionY"] = plane_y
                            plane["PositionYUnit"] = "µm"

                        if plane_z is not None:
                            plane["PositionZ"] = plane_z
                            plane["PositionZUnit"] = "µm"

                        plane_metadata.append(plane)
                        
                        # go to the next plane
                        plane_index += 1

            # Append the plane metadata to the total metadata
            if plane_metadata:
                ome_metadata["Plane"] = plane_metadata

            return ome_metadata

        def tczyx_plane_access(array, T, C, Z):
            """
            Helper function that accesses (Y,X) data given (T,C), computing the Z-stack
            """

            for t in range(T):
                for c in range(C):
                    z_stack = array[t, c, :, :, :].compute()

                    for z in range(Z):
                        yield np.ascontiguousarray(z_stack[z, :, :])

        # Get the output path
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize the writer
        with tifffile.TiffWriter(output_path, bigtiff=True, ome=True) as ome_tif:

            for series in image_series:

                # Get the data form the singular series
                img_array = series["array"]
                img_axes = series["axes"]
                voxel_size_metadata = series["voxel_size_metadata"]
                time_metadata = series["time_metadata"]
                position_metadata = series["position_metadata"]

                # Raise an error if the axes are not in the TCZYX format
                if img_axes != "TCZYX":
                    raise ValueError(f"The series must be TCZYX before writing. Got {img_axes}")

                # Get the dimensions
                T, C, Z, Y, X = img_array.shape

                # Get the OME formatted metadata of the series
                ome_metadata = get_ome_metadata(voxel_size_metadata, time_metadata, position_metadata, T, C, Z)

                # Write this series into the OME-TIF file
                ome_tif.write(
                    data=tczyx_plane_access(img_array, T, C, Z),
                    shape=(T, C, Z, Y, X),
                    dtype=img_array.dtype,
                    photometric="minisblack",
                    metadata=ome_metadata,
                    maxworkers=1,
                )


    #--------------------------------------------------------------------------

    def write_tiff(output_path, image_series):
        """
        Function that takes a list of dictionaries as an input and writes its data into a .tif or .tiff file.
        These .tif and .tiff files are Fiji/ImageJ compatible.
        ImageJ hyperstacks use TZCYX order, which is handled by this writer.
        ImageJ hyperstacks can also only handle 5D data. For this reason, multi-positions are written as different files.
        """

        def tzcyx_plane_access(array, T, C, Z):
            """
            Helper function that accesses (Y,X) data given (T,Z), computing the C-Stack
            """

            for t in range(T):
                for z in range(Z):
                    c_stack = array[t, :, z, :, :].compute()

                    for c in range(C):
                        yield np.ascontiguousarray(c_stack[c, :, :])

        def get_fiji_metadata(T, C, Z, voxel_size_metadata, time_metadata, position_metadata):
            """
            Helper function that computes axes and voxel size metadata for Fiji/ImageJ
            """

            # Start the dictionary
            metadata = {
                "axes": "TZCYX",
                "channels": C,
                "slices": Z,
                "frames": T,
                "hyperstack": True,
                "mode": "composite",
            }

            #-----------------------------------------------------------
            # Get the voxel size metadata
            if voxel_size_metadata["z"] is not None:
                metadata["spacing"] = voxel_size_metadata["z"]

            if (
                voxel_size_metadata["z"] is not None
                or voxel_size_metadata["y"] is not None
                or voxel_size_metadata["x"] is not None
                ):

                # Assume micrometer unit since the reader converts any unit to micrometers
                metadata["unit"] = "um"

            #-----------------------------------------------------------
            # Get the time metadata
            if time_metadata["t"] is not None:
                metadata["finterval"] = time_metadata["t"]


            #-----------------------------------------------------------
            # Get the positional metadata

            position_x = position_metadata.get("x")
            position_y = position_metadata.get("y")
            position_z = position_metadata.get("z")

            voxel_x = voxel_size_metadata.get("x")
            voxel_y = voxel_size_metadata.get("y")
            voxel_z = voxel_size_metadata.get("z")

            # Here we are solving for the origin:
            # physical_x = (x_pixel - xorigin) * voxel_x => physical_x=0 = (0 - xorigin) * voxel_x <=>
            # <=> xorigin = - position_x / voxel_x 

            if position_x is not None and voxel_x not in (None, 0):
                metadata["xorigin"] = - position_x / voxel_x 

            if position_y is not None and voxel_y not in (None, 0):
                metadata["yorigin"] = - position_y / voxel_y

            if position_z is not None and voxel_z not in (None, 0):
                metadata["zorigin"] = - position_z / voxel_z


            return metadata
        
        def get_resolution(voxel_size_metadata):
            """
            Helper function that gets the resolution in pixels/micrometer
            since that is the resolution that Fiji/ImageJ natively recognizes
            """

            if voxel_size_metadata["x"] is None or voxel_size_metadata["y"] is None:
                return None
            
            if voxel_size_metadata["x"] == 0 or voxel_size_metadata["y"] == 0:
                return None
            
            return (
                1 / voxel_size_metadata["x"],
                1 / voxel_size_metadata["y"],
            )
        
        def write_single_tiff(series_output_path, series):
            """
            Helper function that writes a single 5D tif file
            """

            # Get the series data
            img_array = series["array"]
            img_axes = series["axes"]
            voxel_size_metadata = series["voxel_size_metadata"]
            time_metadata = series["time_metadata"]
            position_metadata = series["position_metadata"]

            # Raise an error if the axes are not the correct ones
            if img_axes != "TCZYX":
                raise ValueError(f"The series must be TCZYX before writing. Got {img_axes}")
            
            # Get the shape of the data
            T, C, Z, Y, X = img_array.shape

            # Write the tif file
            with tifffile.TiffWriter(series_output_path, imagej=True) as tif:
                tif.write(
                    data=tzcyx_plane_access(img_array, T, C, Z),
                    shape=(T, Z, C, Y, X),
                    dtype=img_array.dtype,
                    photometric="minisblack",
                    metadata=get_fiji_metadata(T, C, Z, voxel_size_metadata, time_metadata, position_metadata),
                    resolution=get_resolution(voxel_size_metadata),
                )

        # Get the output path
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the tif if there is a single series in the list
        if len(image_series) == 1:
            write_single_tiff(output_path, image_series[0])

        # If there is more than one series in the list
        else:
            # Create the folder in which the positions will be saved in
            output_format_name = output_path.suffix.replace(".", "").upper()

            series_folder = output_path.with_name(
                f"{output_path.name.removesuffix(output_path.suffix)}_{output_format_name}"
            )

            series_folder.mkdir(parents=True, exist_ok=True)

            # Write a file for each of the available series
            for series_index, series in enumerate(image_series, start=1):
                series_output_path = series_folder / (f"series_{series_index}{output_path.suffix}")

                write_single_tiff(series_output_path, series)