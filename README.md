# GElectrical

[Website](https://manuvarkey.github.io/GElectrical) • 
[Documentation](https://gelectrical.readthedocs.io) •
[Forum](https://github.com/manuvarkey/GElectrical/discussions/) •
[Bug tracker](https://github.com/manuvarkey/GElectrical/issues) •
[Git repository](https://github.com/manuvarkey/GElectrical)

[![Release](https://img.shields.io/github/release/manuvarkey/GElectrical.svg)](https://github.com/manuvarkey/GElectrical/releases/latest)
![License](https://img.shields.io/github/license/manuvarkey/GElectrical)

<a href="https://flathub.org/apps/com.kavilgroup.gelectrical"><img height="51" alt="Download on Flathub" src="https://flathub.org/assets/badges/flathub-badge-en.svg"/> </a> 
<a href="https://github.com/manuvarkey/GElectrical/releases/latest"><img height="51" alt="Download for Windows" src="https://raw.githubusercontent.com/manuvarkey/GElectrical/master/source/artwork/windows_badge.svg"/> </a>

GElectrical is a free and opensource electrical system analysis software for LV/MV electrical distribution networks. Following features are currently implemented.

* Schematic capture.
* Pandapower network generation from schematic.
* Power flow time series analysis (Symmetric and Assymetric).
* Power flow with diversity factors (Symmetric and Assymetric).
* Voltage drop analysis.
* Short circuit analysis (Symmetric and SLG).
* Coordination analysis for power supply protection devices with support for CB and fuse protection curves; damage curves for transformers, cables and motors.
* Support for daily load curves for load elements.
* Support for arriving network parameters for custom geometry OH lines.
* Support for modeling networks with mixed TN-S/ TN-C/ TT/ IT earthing systems.
* Electrical rules check for checking conformity with IEC/ local electrical guidelines.
* Print and export of drawings to pdf.
* Generation of analysis reports.

GElectrical uses pandapower as the backend for implementing power flow related functionality like voltage drop and short circuit analysis.

> **Please note that the program is in active development and bugs are expected. Cross checking of generated calculations is reccomended. See [Roadmap](https://github.com/manuvarkey/GElectrical/issues/1) for current limitations.**

## Screenshots

**See [Screencasts](https://www.youtube.com/playlist?list=PLyFdF5OlDZHI8DBi42qsmUeiiD2Cd0eLU) for application screencasts**

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

## Installation

Application can be installed for use on your OS as described below.

> It is reccomended to install `osifont` for schematic capture. This can be downloaded from [https://github.com/hikikomori82/osifont/blob/master/osifont.ttf](https://github.com/hikikomori82/osifont/blob/master/osifont.ttf).

### Binary

#### Windows

Use `.EXE` installation package available under the latest [Release](https://github.com/manuvarkey/GElectrical/releases/latest).

#### Linux

Application is published on `Flathub` repository at [GElectrical](https://flathub.org/apps/details/com.kavilgroup.gelectrical). 

It should be possible to install the application using the default package manager on most linux systems if flathub is setup. Please see [https://flatpak.org/setup/](https://flatpak.org/setup/) to setup flahub for your linux distribution.

### Source

#### Linux

* Install GTK3 from your distribution package manager.
* Run `pip install appdirs pycairo numpy numba scipy pandas mako networkx matplotlib pandapower jinja2 weasyprint openpyxl shapely`.
* Clone this repository `git clone https://github.com/manuvarkey/GElectrical.git`
* Run `gelectrical_launcher.py` from cloned directory.

#### Windows

* Install `git`, `msys2`, `visualstudio2022-workload-vctools` and `gvs_build` by folowing this link [gvsbuild](https://github.com/wingtk/gvsbuild).
* Setup GTK3 and PyGObject development envirnonment using `gvs_build` by running `gvsbuild build --enable-gi --py-wheel gtk3 pygobject adwaita-icon-theme`.
* Add required environment variables as suggested in the above link. Please see [Create and Modify Environment Variables on Windows](https://docs.oracle.com/en/database/oracle/machine-learning/oml4r/1.5.1/oread/creating-and-modifying-environment-variables-on-windows.html) for more information about setting up environment varables.
* Run `pip install appdirs pycairo numpy numba scipy pandas mako networkx matplotlib pandapower jinja2 weasyprint openpyxl shapely` in powershell.
* Clone this repository using `git clone https://github.com/manuvarkey/GElectrical.git`.
* Run `python gelectrical_launcher.py` from the cloned directory.

#### Dependencies:

##### Python 3 (v3.10+)

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

##### GTK3  (v3.36+)
