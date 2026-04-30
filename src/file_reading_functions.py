"""
This file has various functions to read data from each file format either as a zarr or a numpy array
"""

from __future__ import annotations

from os import PathLike
from pathlib import Path

import zarr
from imaris_ims_file_reader import ims


def read_ims_as_zarr(
    file_path: str | PathLike[str],
    resolution_level: int = 0,
):
    """
    Open an Imaris .ims file as a read-only zarr array.
    """

    ims_store = ims(str(file_path), ResolutionLevelLock=resolution_level, aszarr=True)
    return zarr.open(ims_store, mode="r")

    
if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    ims_folder = repo_root / "teste_bruna2"
    ims_files = sorted(ims_folder.glob("*.ims"))

    for ims_file, i in enumerate(ims_files):
        #print(i, ims_file)
        zarr_array = read_ims_as_zarr(ims_file)
        print(f"{ims_file.name}: {zarr_array.shape}")