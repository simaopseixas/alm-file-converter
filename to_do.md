# TO-DO


Things that were found in testing:

- Some OME-Zarr pyramid levels crop image edges. (still need to test the fix)
- Failed/interrupted writes can leave large partial outputs.

---------------------------------------------------------------

- Add the compression and pyramid behavior to complement the checkboxes

- Add .czi reading file format
     
### Future

- Validate the time-frame metadata in all file formats:
    Remaining:
    - lif
    - zarrs - .zarr, .ome.zarr 
    - tifs - .tif, .tiff, .ome.tif, .ome.tiff
    - zvi
    - nd2
