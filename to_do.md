# TO-DO

## Other things

- Add the size of the file being converted in the console
- (maybe) add a compression option when the writing is in .ome.tif or .ome.tiff


## File format support

- Maybe chagne the omezarr writing protocol, since the multiview-stitcher sim is taking some time

- Change the rading of the file formats into the image_series approach:
    remaining:
        .nd2
        tifs - .tif, .itff, .ome.tif, .ome-tiff
        .zvi
        .ims
        zarrs - .zarr, .ome.zarr 

## Metadata

- Preserve series name when available:
    reamining
        .nd2
        tifs - .tif, .itff, .ome.tif, .ome-tiff
        .zvi
        .ims
        zarrs - .zarr, .ome.zarr 

- Preserve time-spacing when available
    reamining
        .nd2
        tifs - .tif, .itff, .ome.tif, .ome-tiff
        .zvi
        .ims
        zarrs - .zarr, .ome.zarr 


- Preserve positional metadata when available
- Add significant bit-depth metadata (important for the case of 12 bit data)


## Output formats