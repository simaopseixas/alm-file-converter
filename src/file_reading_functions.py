"""
This file has various functions to read data from each file format either as a zarr or a numpy array
"""

from __future__ import annotations

from os import PathLike

import zarr
from imaris_ims_file_reader import ims


def read_ims_as_zarr(
    file_path: str | PathLike[str],
    res_level: int = 0,
):
    """
    Open an Imaris .ims file as a read-only zarr array.
    """

    ims_store = ims(str(file_path), resolution_level=res_level, aszarr=True)
    return zarr.open(ims_store, mode="r")