# TO-DO

Before release:

- check time-frame metadata writing

- check the error in which a file was written without pyramids and then I wrote the same file with pyramids and an error emerged.

---------------------------------------------------------------

Things that were found in testing:

- Failed/interrupted writes can leave large partial outputs.


### Future

- Add .czi reading file format

- Validate the time-frame metadata in all file formats:
    Remaining:
    - lif
    - zarrs - .zarr, .ome.zarr 
    - tifs - .tif, .tiff, .ome.tif, .ome.tiff
    - zvi
    - nd2
