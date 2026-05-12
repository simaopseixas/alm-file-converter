## General Description

ALM Microscopy File Converter is a tool for converting microscopy image files into other formats.

The program currently supports the following input formats:
`.ims`, `.lif`, `.ome.tiff`, `.ome.zarr`, `.zarr`

and supports convertion to the following output formats:
`.ome.zarr` (more will be added)

The converter can be used in two modes:

1. **Batch Conversion**, where all supported files inside a selected folder are converted.
2. **Single-file Conversion*, where the user selects one microscopy file to be converted

The program is designed to work with large microscopy datasets by relying on lazy loading through Zarr/Dask, reducing the need to load the entire dataset into memory at once.

If an error occurs during batch conversion, the program skips the failed file and continues converting the remaining files. At the end, a report is generated listing the failed files and its error traceback.

A standalone executable is also available as a Release, which can also be built using PyInstaller.

---

## Running the code

You will need a Python installation.

This project uses Python 3.10.

**Windows:**

```bat
setup_venv.bat
.venv\Scripts\activate
python src/main.py
```
  

**macOS/Linux:**

```sh
./setup_venv.sh
source .venv/bin/activate
python src/main.py
```

---

## Building the Executable

To build the standalone executable, run:
```
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean "ALM File Converter.spec"
```


---

## Program usage

1. Run the executable or start the program from Python, by running main.py
2. Choose the desired output format.
3. Use **Batch Processing** if you want to convert all supported files that you have inside a folder.
4. Disable **Batch Processing** if you want to convert a single file.
5. In single-file mode, choose either:
    - **Select Microscopy File** for `.ims`, `.lif` or `.ome.tiff` files.
    - **Select OME-Zarr/Zarr File** for `.ome.zarr` or `.zarr` files.
6. Wait for the conversion to finish

---

## Output

Converted files are saved inside a new folder named `\Converted Files` which is created inside the selected input folder, or next to the selected input file.

If any file fails during batch conversion, a timestamped report is saved in that same output folder: `conversion_report_YYYY-MM-DD_HH-MM-SS.txt`

The report contains:
- Total number of files.
- Number of successfully converted files.
- Number of failed files.
- List of failed files.
- Error tracebacks.

---

## Author

**Simão Peniche Seixas**

simao.seixas@i3s.up.pt  
simao.peniche.seixas@gmail.com  
i3S - Institute for Research and Innovation in Health
