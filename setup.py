from setuptools import setup, find_packages 

setup(
    # Application name:
    name="GElectrical",

    # Version number (initial):
    version="1-beta",

    # Application author details:
    author="Manu Varkey",
    author_email="manuvarkey@gmail.com",

    # Packages
    packages = ['gelectrical', 'gelectrical.model', 'gelectrical.view', 'gelectrical.elementmodel'],
    include_package_data = True, # Include additional files into the package

    # Details
    maintainer="Manu Varkey",
    maintainer_email="manuvarkey@gmail.com",
    url="https://github.com/manuvarkey/GElectrical",
    license="GPL-3.0",
    description="A free and opensource electrical system analysis software for LV/MV electrical distribution networks.",

    long_description= 'A free and opensource electrical system analysis software for LV/MV electrical distribution networks.',
    
    install_requires=["appdirs", "pycairo", "numpy", "numba", "scipy", "pandas", "mako", "networkx", "matplotlib", "pandapower", "jinja2", "weasyprint", "openpyxl", "shapely", "PyGObject"],
   
    
    classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          'Topic :: Scientific/Engineering',
          ],
)
