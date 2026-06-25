# TO-DO


Things that were found in testing:

- Some OME-Zarr pyramid levels crop image edges.
- OME-Zarr fabricates unknown metadata as 1.0 scales and (0,0,0) positions.
- Large conversions provide no progress indication.
- Failed/interrupted writes can leave large partial outputs.

---------------------------------------------------------------

- Add a compression checkbox

- Maybe add a checkbox for pyramid writing in omezarr writing

- Add .czi reading file format
     
### Future

- Preserve time-spacing when available
    reamining
        .ims (I WILL NEED A TIME FRAME FILE)
- ? maybe add the available pyramids of .ims datasets to the reading and writing protocols
- Add significant bit-depth metadata (important for the case of 12 bit data)

- Validate the time-frame metadata in all file formats:
    Remaining:
    - lif
    - zarrs - .zarr, .ome.zarr 
    - tifs - .tif, .tiff, .ome.tif, .ome.tiff
    - zvi
    - nd2
