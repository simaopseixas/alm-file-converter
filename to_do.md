# TO-DO

# Other things

- see if i do actually convert the read zarr into dask
- add the writing of an "error_report.txt" in the case of a single microscopy file getting an error

## File format support

- Add .zvi reading support

# Metadata

- Verify all tifs metadata for non-OME and OME
- Preserve channel names when available
- Preserve time-spacing when available
- Preserve positional metadata when available
- Add significant bit-depth metadata (important for the case of 12 bit data)

# Output formats

- Add .zarr support