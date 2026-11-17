PlotBench import test files (synthetic data, made by make_test_files.py; author Kishan Tiwari)
Every file can also be dragged onto the PlotBench window.

oxides_comma.csv
    Open with: File > Quick Import CSV / TXT, Import Wizard, or drag onto the window
    Expect:    5 rows x 9 columns: Sample, SiO2 ... K2O (SiO2 of B-1 = 49.1)

oxides_semicolon_decimal_comma.csv
    Open with: File > Import Wizard: Delimiter = Semicolon, Decimal separator = ','
    Expect:    same table as oxides_comma.csv (European style: 49,1 becomes 49.1)

spectrum_tab.tsv
    Open with: Quick Import or Import Wizard (Tab)
    Expect:    221 rows, X 100-1200 cm-1, peaks near 465 and 820 cm-1

spectrum_whitespace.txt
    Open with: Quick Import, or Import Wizard with 'Space(s) / whitespace'
    Expect:    same spectrum, two columns

spectrum_with_header.dat
    Open with: File > Import Wizard: Skip lines at top = 3, names line 1, units line 2, comments line 3
    Expect:    221 rows; the column units (cm-1, counts) and comments go to the Units and Comments header rows

oxides_pipe.txt
    Open with: File > Import Wizard: Delimiter = Pipe |
    Expect:    same table as oxides_comma.csv

spectrum.prn
    Open with: drag onto the window (or Quick Import with 'All files')
    Expect:    56 rows, two columns X and Y

spectrum.asc
    Open with: drag onto the window (or Quick Import with 'All files')
    Expect:    56 rows, two columns X and Y

detection_limits.csv
    Open with: Quick Import
    Expect:    text cells such as '<0.05', 'n.d.' and 'bdl' are kept as text; plotted as censored values in spider plots

workbook_two_sheets.xlsx
    Open with: File > Import Excel (or drag)
    Expect:    one workbook with two sheets, Oxides (5 x 9) and Spectrum (221 x 2)

two_spots.png / .jpg / .tif / .bmp / .gif
    Open with: File > Import Image as Matrix (or drag)
    Expect:    a 120 x 160 matrix with two bright spots; the brightest is at column 60, 50 pixels from the top of the image (matrix row 70, as row 1 is at the bottom); JPG and GIF differ slightly (compression, palette)

graph_to_digitize_log_axis.png
    Open with: Tools > Digitizer: calibrate X with 0 and 1600 (or two labelled ticks), Y with 10^-19 and 10^-9 (type them as 10^-19, 1e-9 ...); it will offer a log Y axis
    Expect:    7 points: (200, 1e-18), (400, 3e-17), (600, 2e-15), (800, 5e-14), (1000, 1e-12), (1200, 4e-11), (1400, 2e-10)

arrays.h5
    Open with: File > Import HDF5 / NetCDF / MATLAB
    Expect:    datasets run1/time and run1/signal (101 values, a damped cosine) and image (40 x 60, as matrix)

climate_classic.nc
    Open with: File > Import HDF5 / NetCDF / MATLAB
    Expect:    time and temperature (24 values, 7 to 23) and field (10 x 12, as matrix)

matlab_v5.mat
    Open with: File > Import HDF5 / NetCDF / MATLAB
    Expect:    wavelength and absorbance (31 values, peak at 520 nm) and M (40 x 60)

matlab_v73.mat
    Open with: File > Import HDF5 / NetCDF / MATLAB
    Expect:    MATLAB 7.3 (HDF5) file: wavelength (31 values) and M (40 x 60, same as matlab_v5.mat)

ftir_xydata.jdx
    Open with: File > Import JCAMP-DX Spectrum
    Expect:    451 points from 4000 to 400 1/cm, bands at 1650 and 2920 1/cm (absorbance up to about 0.62)

peaks_table.dx
    Open with: File > Import JCAMP-DX Spectrum
    Expect:    3 points: (1650, 0.62), (2920, 0.42), (3400, 0.15)

samples.db
    Open with: File > Import from SQLite Database: pick a table, or type SQL such as SELECT * FROM oxides WHERE SiO2 > 55
    Expect:    tables oxides (5 rows) and sites (2 rows); the SQL example returns 3 rows

legacy_excel97.xls
    Open with: File > Import Excel
    Expect:    the Oxides table (5 x 9) in the old Excel 97-2003 format
