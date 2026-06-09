# TO-DO

- correct the ome zarr write to use v0.4 again. The v0.5 cannot be naturally opened in Fiji

- correct the error of when a conversion is happening and I open the logger, the main window also appears

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
