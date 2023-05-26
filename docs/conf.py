# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'GElectrical'
copyright = '2023, Manu Varkey'
author = 'Manu Varkey'
release = 'v1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['myst_parser']

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_css_files = ['css/custom.css',]

# -- Options for latex output

latex_table_style: ['booktabs', 'colorrows']
#latex_engine = 'luatex'
latex_elements = {
'papersize': 'a4paper',
'pointsize': '11pt',
'preamble': r'''
    \usepackage{mdframed}
    \renewcommand{\sfdefault}{lmdh}
    \renewcommand{\rmdefault}{lmr}
    \renewcommand{\ttdefault}{lmtt}
    
    \renewenvironment{sphinxnote}[1]%
    {\vspace{5mm}
     \begin{mdframed}[topline=false,bottomline=false, rightline=false,
		    linewidth=2pt, frametitle={#1}]}%
		    {\end{mdframed}
     \vspace{5mm}}
    '''
}
