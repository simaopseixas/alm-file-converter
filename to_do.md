# TO-DO

## Other things

- In batch conversion change the "Conversion Files" folder to say the output file format (ex: "Conversion_Files_omezarr")
- Add the size of the file being converted in the console
- (maybe) add a compression option when the writing is in .ome.tif or .ome.tiff


## File format support

- Maybe chagne the omezarr writing protocol, since the multiview-stitcher sim is taking some time
- Add multi-series/position data in ome-tiff and ome.tif - I think I will need to do a sequential read->write of a series at a time onto the same file. So I cannot create an entire MTCZYX dask array at once
- change the series reading in .lif and .nd2 to handle the writing in the file to be one series at a time. This would need the computation of one dask array per available series.

## Metadata

- Preserve channel names when available (if really necessary)
- Preserve time-spacing when available
- Preserve positional metadata when available
- Add significant bit-depth metadata (important for the case of 12 bit data)


## Output formats