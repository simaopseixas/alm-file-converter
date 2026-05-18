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

from bioio import BioImage
import bioio_bioformats

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
            Get voxel size metadata, time frame and series name from OME or Imagej standard TIFF metadata.
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
            # Series Name

            name_metadata = f"Series {series_index + 1:03d}"

            # Get the series name if OME available or not
            if ome_image is not None and ome_image.get("Name") is not None:
                name_metadata = str(ome_image["Name"])

            return voxel_size_metadata, time_metadata, name_metadata

        
    
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
                voxel_size_metadata, time_metadata, series_name = get_tif_metadata(tif, tif_series, series_index)

                # Append the information onto the dictionary
                image_series.append({
                    "array": img_array,
                    "axes": img_axes,
                    "voxel_size_metadata": voxel_size_metadata,
                    "time_metadata": time_metadata,
                    "name": series_name
                })

        if not image_series:
            raise ValueError(f"No readable image series found in file: {file_path}")
        
        return image_series
    
    #--------------------------------------------------------------------------

    def read_omezarr_as_dask(file_path):
        """
        Opens a .zarr or an .ome.zarr as a zarr array in reading.
        Then converts it to a dask array.
        """

        # Access the ome.zarr in reading mode
        sim = ngff_utils.read_sim_from_ome_zarr(file_path, resolution_level=0)
        img_array = sim.data

        # Get the voxel size data
        spacing = si_utils.get_spacing_from_sim(sim)

        # Get the voxel size metadata if available
        voxel_size_metadata = {
            "z": spacing.get("z", None),
            "y": spacing.get("y", None),
            "x": spacing.get("x", None),
        }

        # Get the available axes of the data
        img_axes = "".join(sim.dims).upper()


        return img_array, voxel_size_metadata, img_axes
    
    
    #--------------------------------------------------------------------------


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

        # Get voxel data from ims physical extents given by the metadata
        Z, Y, X = img_array.shape[-3:]

        x_extent = ( ims_store.ims.read_numerical_dataset_attr("ExtMax0") - ims_store.ims.read_numerical_dataset_attr("ExtMin0") )
        y_extent = ( ims_store.ims.read_numerical_dataset_attr("ExtMax1") - ims_store.ims.read_numerical_dataset_attr("ExtMin1") )
        z_extent = ( ims_store.ims.read_numerical_dataset_attr("ExtMax2") - ims_store.ims.read_numerical_dataset_attr("ExtMin2") )

        voxel_size_metadata = {
            "z": z_extent / Z if Z > 1 else None,
            "y": y_extent / Y if Y > 1 else None,
            "x": x_extent / X if X > 1 else None,
        }

        img_axes = "TCZYX"

        return img_array, voxel_size_metadata, img_axes
    

    #--------------------------------------------------------------------------

    def read_lif_as_dask(file_path):
        """
        Opens a Leica .lif file.
        Returns a list of independent 5D TCZYX image series dictionaries
        with the series dask array, axes and voxel size data.
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

            # Get the voxel size metadata
            x_scale, y_scale, z_scale, t_scale = img.info["scale"]
            voxel_size_metadata = {
                "z": 1 / z_scale if z_scale else None,
                "y": 1 / y_scale if y_scale else None,
                "x": 1 / x_scale if x_scale else None,
            }

            # Get time metadata
            time_metadata = {"t": 1 / t_scale if t_scale else None} # in seconds

            # For each mosaic inside the "series"
            for m in range(M):

                # Compute the TCZYX dask array
                image_array = build_tczyx_array(file_path, image_index, img, m)

                # Get the series name
                image_name = getattr(img, "name", f"Series{image_index + 1:03d}")

                # Get the number of the mosaic if there are more mosaics available
                if M > 1:
                    image_name = f"{image_name}"

                # Append the mosaic information on the list
                image_series.append({
                    "array": image_array,
                    "axes": "TCZYX",
                    "voxel_size_metadata": voxel_size_metadata,
                    "time_metadata": time_metadata,
                    "name": image_name,
                })

        return image_series

    
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
        voxel_size_metadata = {
            "z": voxel_size.z if voxel_size.z else None,
            "y": voxel_size.y if voxel_size.y else None,
            "x": voxel_size.x if voxel_size.x else None,
        }

        return img_array, voxel_size_metadata, img_axes
    
    #--------------------------------------------------------------------------

    def read_zvi_as_dask(file_path):
        """
        Opens a Zeiss .zvi as a dask array.
        This function doesn't function lazily. Since .zvi doesn't support lazy reading, 
        the whole dataset is loaded into memory as a numpy array and converted to dask.
        """

        # Access the .zvi file
        img = BioImage(file_path, reader=bioio_bioformats.Reader)

        # Get the data into numpy
        img_array = img.get_image_data("TCZYX")

        # Get voxel size metadata, if accessible through Bio-Formats
        voxel_sizes = img.physical_pixel_sizes

        voxel_size_metadata = {
            "z": voxel_sizes.Z,
            "y": voxel_sizes.Y,
            "x": voxel_sizes.X
        }

        # Convert the numpy array to dask, to make it compatible with the conversion pipeline
        img_array = dask.array.from_array(
            img_array,
            chunks=(1,1,1,img_array.shape[-2],img_array.shape[-1])
        )

        img_axes = "TCZYX"

        return img_array, voxel_size_metadata, img_axes
    
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

        # Multi-position files need to keep M as the first dimension
        # Otherwise, all files are normalized to standard TCZYX
        target_axes = "MTCZYX" if "M" in img_axes else "TCZYX"

        # Add any missing dimensions in their final target positions
        for dim in target_axes:
            if dim not in img_axes:
                axis = target_axes.index(dim)
                img_array = dask.array.expand_dims(img_array, axis=axis)
                img_axes = img_axes[:axis] + dim + img_axes[axis:]

        # Reorder the existing dimensions into the required order
        axis_order = [img_axes.index(dim) for dim in target_axes]
        img_array = dask.array.transpose(img_array, axis_order)

        return img_array, target_axes

    #--------------------------------------------------------------------------
    
    def write_ome_zarr(
            output_path,
            img_array,
            img_dims,
            img_axes,
            voxel_size_metadata,
    ):
        """
        Function that takes a dask array as an input and writes its data into an .ome.zarr file
        """
        
        output_path = Path(output_path)

        # Compute the voxel size metadata to write
        scale = {
            "z": voxel_size_metadata["z"] if voxel_size_metadata["z"] is not None else 1,
            "y": voxel_size_metadata["y"] if voxel_size_metadata["y"] is not None else 1,
            "x": voxel_size_metadata["x"] if voxel_size_metadata["x"] is not None else 1,
        }
        
        # If the file that was read has 6 available dimensions, meaning Mosaics + TCZYX
        if img_axes == "MTCZYX":

            # Get the dimensions
            M, T, C, Z, Y, X = img_dims

            # Create e new folder for the mosaics to be saved to
            output_format_name = ".ome.zarr".replace(".", "")

            mosaic_folder = output_path.with_name(
                f"{output_path.name.removesuffix('.ome.zarr')}_{output_format_name}"
            )

            mosaic_folder.mkdir(parents=True, exist_ok=True)

            for m in range(M):

                # for testing convenience
                # if m + 1 > 2:
                #     break

                # Change the name of the output mosaic filename
                mosaic_output_path = mosaic_folder / (
                    f"{output_path.name.removesuffix('.ome.zarr')}_mosaic_{m + 1}.ome.zarr"
                )

                sim = si_utils.get_sim_from_array(
                    img_array[m,:,:,:,:,:],
                    dims = ["t", "c", "z", "y", "x"],
                    scale=scale,
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
                scale=scale,
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

    def write_ome_tiff(output_path, image_series):
        """
        Function that takes a list of dask arrays as an input and writes its data into an .ome.tif or .ome.tiff file
        """

        def get_ome_metadata(voxel_size_metadata, time_metadata, image_name):
            """
            Helper function that computes an OME voxel size dictionary for metadata
            """

            # Create the OME metadata dictionary
            ome_metadata = { "axes": "TCZYX",
                             "Name": image_name}

            if voxel_size_metadata["x"] is not None:
                ome_metadata["PhysicalSizeX"] = voxel_size_metadata["x"]

            if voxel_size_metadata["y"] is not None:
                ome_metadata["PhysicalSizeY"] = voxel_size_metadata["y"]

            if voxel_size_metadata["z"] is not None:
                ome_metadata["PhysicalSizeZ"] = voxel_size_metadata["z"]

            if time_metadata["t"] is not None:
                ome_metadata["TimeIncrement"] = time_metadata["t"]
                ome_metadata["TimeIncrementUnit"] = "s"

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
                image_name = series["name"]

                # Raise an error if the axes are not in the TCZYX format
                if img_axes != "TCZYX":
                    raise ValueError(f"The series must be TCZYX before writing. Got {img_axes}")

                # Get the dimensions
                T, C, Z, Y, X = img_array.shape

                # Get the OMe formatted metadata of the series
                ome_metadata = get_ome_metadata(voxel_size_metadata, time_metadata, image_name)

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

    def write_tiff(
            output_path,
            img_array,
            img_dims,
            img_axes,
            voxel_size_metadata,
    ):
        """
        Function that takes a dask array as an input and writes its data into a .tif or .tiff file.
        These .tif and .tiff files are Fiji/ImageJ compatible.
        ImageJ hyperstacks use TZCYX order, which is handled by this writer.
        ImageJ hyperstacks can also only handle 5D data. For this reason, multi-positions are written as different files.
        """

        # Get the output path
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def tzcyx_plane_access(array, T, C, Z):
            """
            Helper function that accesses (Y,X) data given (T,Z), computing the C-Stack
            """

            for t in range(T):
                for z in range(Z):
                    c_stack = array[t, :, z, :, :].compute()

                    for c in range(C):
                        yield np.ascontiguousarray(c_stack[c, :, :])

        def get_fiji_metadata(T, C, Z, voxel_size_metadata):
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

            if voxel_size_metadata["z"] is not None:
                metadata["spacing"] = voxel_size_metadata["z"]

            if (
                voxel_size_metadata["z"] is not None
                or voxel_size_metadata["y"] is not None
                or voxel_size_metadata["x"] is not None
                ):

                # Assume micrometer unit since the reader converts any unit to micrometers
                metadata["unit"] = "um"

            return metadata
        
        def get_resolution():
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
        

        
        # Check the axes of the input file to write accordingly
        if img_axes == "MTCZYX":

            # Get the dimensions
            M, T, C, Z, Y, X = img_dims

            # Create the folder in which the positions will be saved in
            output_format_name = output_path.suffix.replace(".", "")

            mosaic_folder = output_path.with_name(
                f"{output_path.name.removesuffix(output_path.suffix)}_{output_format_name}"
            )

            mosaic_folder.mkdir(parents=True, exist_ok=True)

            for m in range(M):

                # for testing convenience
                # if m + 1 > 4:
                #     break
                

                mosaic_output_path = mosaic_folder / (
                    f"{output_path.stem}_mosaic_{m + 1}{output_path.suffix}"
                )

                # Initialize the writer
                with tifffile.TiffWriter(mosaic_output_path, imagej=True) as tif:
                    tif.write(
                        data=tzcyx_plane_access(img_array[m, :, :, :, :, :], T, C, Z),
                        shape=(T, Z, C, Y, X),
                        dtype=img_array.dtype,
                        photometric="minisblack",
                        metadata=get_fiji_metadata(T, C, Z, voxel_size_metadata),
                        resolution=get_resolution(),
                    )

        else:

            T, C, Z, Y, X = img_dims

            # Initialize the writer
            with tifffile.TiffWriter(output_path, imagej=True) as tif:
                tif.write(
                    data=tzcyx_plane_access(img_array, T, C, Z),
                    shape=(T, Z, C, Y, X),
                    dtype=img_array.dtype,
                    photometric="minisblack",
                    metadata=get_fiji_metadata(T, C, Z, voxel_size_metadata),
                    resolution=get_resolution(),
                )

    #--------------------------------------------------------------------------

# if __name__ == "__main__":

#     file = r"C:\Users\simao\Desktop\Repositories\Microscopy_File_Converter\files_for_conversion\lixo\MosaicoIIrregular_Leica.lif"
    
# #     file = 
    
#     image_series = file_reading_functions.read_lif_as_dask(file)

#     print(image_series)