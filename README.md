# GElectrical

GElectrical is a graphical frontend to pandapower for power supply simulation and analysis with emphasis on electrical distribution and utilisation networks.

Program is in early development with following features currently implemented/ in active developmnet.

* Schematic capture.
* Pandapower network generation from schematic.
* Power flow time series analysis (Symmetric and Assymetric).
* Voltage drop analysis.
* Short circuit analysis (Symmetric and SLG).
* Coordination analysis for power supply protection devices with support for CB and fuse protection curves; damage curves for transformers, cables and motors.
* Support for daily load curves for load elements.
* Support for arriving network parameters for custom geometry OH lines.
* Electrical rules check for checking conformity with IEC/ local electrical guidelines.
* Print and export of drawings to pdf.
* Generation of analysis reports.

## Screenshots

![Properties display](https://raw.githubusercontent.com/manuvarkey/GElectrical/master/screenshots/1.png)
![Results display](https://raw.githubusercontent.com/manuvarkey/GElectrical/master/screenshots/2.png)
![Electrical rules check](https://raw.githubusercontent.com/manuvarkey/GElectrical/master/screenshots/3.png)
![Protection curve display](https://raw.githubusercontent.com/manuvarkey/GElectrical/master/screenshots/4.png)
![Load profile display](https://raw.githubusercontent.com/manuvarkey/GElectrical/master/screenshots/5.png)
![Database display](https://raw.githubusercontent.com/manuvarkey/GElectrical/master/screenshots/6.png)

## Samples

[Sample schematic](https://raw.githubusercontent.com/manuvarkey/GElectrical/master/sample_files/sample_drawing.pdf)
[Sample report](https://raw.githubusercontent.com/manuvarkey/GElectrical/master/sample_files/sample_report.pdf)
[Sample project file](https://github.com/manuvarkey/GElectrical/raw/master/sample_files/sample.gepro)

## Dependencies:

### Python 3 (v3.10+)

Python Modules:

* undo - Included along with distribution.
* appdirs (v1.4.4) - Not included
* openpyxl - Not included
* mako - Not included
* numba - Not included
* pandapower (v2.10.1) - Not included
* numpy - Not included
* pandas - Not included
* networkx - Not included
* shapely - Not included
* matplotlib (v3.5.1) - Not included
* jinja2 - Not included
* weasyprint - Not included
* pycairo - Not included
* PyGObject - Not included

### GTK3  (v3.36+)
