# TO-DO

- Add .czi reading file format

- Preserve positional metadata reading when available
    - [X] lif
    - [X] ome.zarr
    - [X] zvi
    - [X] nd2
    - [X] lif
    - [X] ims
    - [X] tif
    - [X] tiff
    - [X] ome.tif
    - [X] ome.tiff

- Write positional metadata onto the available file formats:
    - [X] ome.zarr
    - [X] tif
    - [X] tiff
    - [X] ome.tif
    - [X] ome.tiff
     
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
