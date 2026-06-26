# TO-DO

Before release:

- check time-frame metadata writing

- Add the compression and pyramid behavior to complement the checkboxes

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
