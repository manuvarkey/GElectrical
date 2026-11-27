from setuptools import setup, find_packages 

setup(
    # Application name:
    name="GElectrical",

    # Version number (initial):
    version="1-1",

    # Application author details:
    author="Manu Varkey",
    author_email="manuvarkey@gmail.com",

    # Packages
    packages = find_packages(include=['gelectrical', 'gelectrical.*']),
    include_package_data = True, # Include additional files into the package

    # Details
    maintainer="Manu Varkey",
    maintainer_email="manuvarkey@gmail.com",
    url="https://github.com/manuvarkey/GElectrical",
    license="GPL-3.0",
    description="A free and opensource electrical system analysis software for LV/MV electrical distribution networks.",

    long_description= 'A free and opensource electrical system analysis software for LV/MV electrical distribution networks.',
    
    # Python and pandapower/WeasyPrint versions: ADR 0015 and ADR 0016
    # (docs/decisions). Keep in sync with pixi.toml and requirements.txt.
    python_requires=">=3.14,<3.15",
    install_requires=["appdirs", "pycairo", "numpy>=1.26,<2.5", "numba>=0.68", "scipy>=1.15",
                      "pandas~=2.3", "mako", "networkx~=3.6", "matplotlib", "pandapower==3.5.6",
                      "jinja2", "weasyprint==70.0", "openpyxl", "shapely", "PyGObject"],
   
    
    classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          'Topic :: Scientific/Engineering',
          ],
)
