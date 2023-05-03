# Installation

Application can be installed for use on your OS as below.

```{admonition} Font for schematic drawings
It is recommended to install `osifont` for schematic capture. This can be downloaded from [https://github.com/hikikomori82/osifont/blob/master/osifont.ttf](https://github.com/hikikomori82/osifont/blob/master/osifont.ttf).
```

## Binary

### Windows

Use `.EXE` installation packages available under the latest [Release](https://github.com/manuvarkey/GElectrical/releases/latest).

### Linux

Application is published on `Flathub` repository at [GElectrical](https://flathub.org/apps/details/com.kavilgroup.gelectrical). 

It should be possible to install the application using the default package manager on most linux systems if flathub is setup. Please see [https://flatpak.org/setup/](https://flatpak.org/setup/) to setup flahub for your linux distribution.

## Source

### Linux

* Install GTK3 from your distribution package manager.
* Run `pip install appdirs pycairo numpy numba scipy pandas mako networkx matplotlib pandapower jinja2 weasyprint openpyxl shapely`.
* Clone this repository `git clone https://github.com/manuvarkey/GElectrical.git`
* Run `gelectrical_launcher.py` from cloned directory.

### Windows

* Install `git`, `msys2`, `visualstudio2022-workload-vctools` and `gvs_build` by folowing this link [gvsbuild](https://github.com/wingtk/gvsbuild).
* Setup GTK3 and PyGObject development envirnonment using `gvs_build` by running `gvsbuild build --enable-gi --py-wheel gtk3 pygobject adwaita-icon-theme`.
* Add required environment variables as suggested in the above link. Please see [Create and Modify Environment Variables on Windows](https://docs.oracle.com/en/database/oracle/machine-learning/oml4r/1.5.1/oread/creating-and-modifying-environment-variables-on-windows.html).
* Run `pip install appdirs pycairo numpy numba scipy pandas mako networkx matplotlib pandapower jinja2 weasyprint openpyxl shapely` in powershell.
* Clone this repository using `git clone https://github.com/manuvarkey/GElectrical.git`.
* Run `python gelectrical_launcher.py` from the cloned directory.

### Dependencies

* Python 3 (v3.10+)
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

* GTK3  (v3.36+)

