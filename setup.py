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
    packages = ['gelectrical'],
    include_package_data = True, # Include additional files into the package

    # Details
    maintainer="Manu Varkey",
    maintainer_email="manuvarkey@gmail.com",
    url="https://github.com/manuvarkey/GElectrical",
    license="GPL-3.0",
    description="GElectrical is a graphical frontend to pandapower for power supply simulation and analysis with emphasis on electrical distribution and utilisation networks.",

    long_description= 'GElectrical is a graphical frontend to pandapower for power supply simulation and analysis with emphasis on electrical distribution and utilisation networks.',
    
    install_requires=["appdirs", "openpyxl", "pandapower", "pandas", "matplotlib", "jinja2", "weasyprint", "pycairo", "PyGObject"],
    
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
