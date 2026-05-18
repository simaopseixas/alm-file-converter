# TO-DO

- Add the size of the file being converted in the console

- Add the available pyramids of .ims datasets to the reading and writing protocols

- Change the reading of the file formats into the image_series approach:
    remaining:
        zarrs - .zarr, .ome.zarr
        tifs

- Validate the time-frame metadata in all file formats:
    Remaining:
    - lif
    - ims
    - zarrs - .zarr, .ome.zarr 
    - tifs - .tif, .tiff, .ome.tif, .ome.tiff
    - zvi
    - nd2

- Preserve time-spacing when available
    reamining
        .ims (I WILL NEED A TIME FRAME FILE)
        zarrs - .zarr, .ome.zarr 

- Preserve positional metadata when available

### Future

- Maybe change the omezarr writing protocol, since the multiview-stitcher sim is taking some time
- Add significant bit-depth metadata (important for the case of 12 bit data)
- Add 6D support for ZARR reading?

