# TO-DO

## Other things

- Maybe chagne the omezarr writing protocol, since the multiview-stitcher sim is taking some time
- Add a compression option when the writing is in .ome.tif or .ome.tiff
- Add multi-series/position data in ome-tiff and ome.tif - I think I will need to do a sequential read->write of a series at a time onto the same file. So I cannot create an entire MTCZYX dask array at once
- change the series reading in .lif and maybe in .nd2

## File format support

## Metadata

- Preserve channel names when available
- Preserve time-spacing when available
- Preserve positional metadata when available
- Add significant bit-depth metadata (important for the case of 12 bit data)


## Output formats