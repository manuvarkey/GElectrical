#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# graph
#
#  Copyright 2014 Manu Varkey <manuvarkey@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

"""Report graphs rendered with Matplotlib without a GUI backend.

``GraphImage`` draws on a plain ``matplotlib.figure.Figure`` (no pyplot, no
GTK canvas); ``savefig`` uses Matplotlib's non-interactive renderers.
"""

import logging, math, base64
from io import BytesIO

from matplotlib.figure import Figure
import matplotlib.style as mplstyle
from matplotlib import ticker

# local files import
from ..core import constants, style
from ..model.graph import GraphModel

mplstyle.use('fast')

# Get logger object
log = logging.getLogger(__name__)


class GraphImage():
    """Class for handling graph image"""
    
    def __init__(self, xlim, ylim, title='', xlabel='', ylabel='', inactivate=False, graph_params={}):
        self.xlim = xlim
        self.ylim = ylim
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.graph_params = graph_params
        self.models = []
        self.colors = constants.GRAPH_COLORS
        # Plot
        self.figure = Figure()
        self.plot = self.figure.add_subplot(111)
        
    def add_plot(self, graph_model):
        self.models.append(GraphModel(graph_model))
        
    def add_plots(self, graph_models):
        for model in graph_models:
            self.add_plot(model)
        
    def clear_plots(self):
        self.models.clear()
        self.model = None
    
    def plot_graph(self):
        self.plot.clear()

        formatter = ticker.StrMethodFormatter('{x:,.6g}')
        for tick in self.plot.get_xticklabels():
            tick.set_fontname(style.REPORT_GRAPH_FONT_FACE)
            tick.set_fontsize(style.REPORT_GRAPH_FONT_SIZE)
        for tick in self.plot.get_yticklabels():
            tick.set_fontname(style.REPORT_GRAPH_FONT_FACE)
            tick.set_fontsize(style.REPORT_GRAPH_FONT_SIZE)
        if not(math.isnan(self.xlim[0]) or math.isnan(self.xlim[1])) and self.xlim[0] != self.xlim[1]:
            self.plot.set_xlim(self.xlim[0], self.xlim[1])
        if len(self.xlim) == 4 and self.xlim[3] == 'log':
            self.plot.set_xscale('log')
        self.plot.xaxis.set_major_formatter(formatter)
        
        if not(math.isnan(self.ylim[0]) or math.isnan(self.ylim[1])) and self.ylim[0] != self.ylim[1]:
            self.plot.set_ylim(self.ylim[0], self.ylim[1])
        if len(self.ylim) == 4 and self.ylim[3] == 'log':
            self.plot.set_yscale('log')
        self.plot.yaxis.set_major_formatter(formatter)
            
        self.plot.grid(True, which='major', alpha=0.3, color=style.COLOR_GRID)
        self.plot.minorticks_on()
        # self.plot.grid(True, which='minor', alpha=0.1, color=style.COLOR_GRID)

        if 'marker' in self.graph_params and not self.graph_params['marker']:
            opt_marker = ''
        else:
            opt_marker = 'o'
        
        for slno, model in enumerate(self.models):
            color = self.colors[slno % len(self.colors)]
            if model.mode == constants.GRAPH_DATATYPE_PROFILE:
                self.plot.plot(model.xval, model.yval, label=model.title, 
                                marker=opt_marker, markersize=4, color=color)
            elif model.mode == constants.GRAPH_DATATYPE_FREE:
                self.plot.scatter(model.xval, model.yval, label=model.title, 
                                marker=opt_marker, markersize=4, color=color)
            elif model.mode == constants.GRAPH_DATATYPE_POLYGON:
                self.plot.fill(model.xval, model.yval, label=model.title, 
                                color=color, alpha=0.2)
                self.plot.fill(model.xval, model.yval, 
                                color='none', edgecolor=color, linewidth=2)
            elif model.mode == constants.GRAPH_DATATYPE_MARKER:
                self.plot.plot(model.xval, model.yval, label=model.title, color=color, 
                               linestyle='dashed', linewidth=1)

        self.plot.set_title(self.title, fontname=style.REPORT_GRAPH_FONT_FACE, fontsize=style.REPORT_GRAPH_FONT_SIZE)
        self.plot.set_xlabel(self.xlabel, fontname=style.REPORT_GRAPH_FONT_FACE, fontsize=style.REPORT_GRAPH_FONT_SIZE)
        self.plot.set_ylabel(self.ylabel, fontname=style.REPORT_GRAPH_FONT_FACE, fontsize=style.REPORT_GRAPH_FONT_SIZE)

        if len(self.models) > 1:
            self.plot.legend(prop={'family':style.REPORT_GRAPH_FONT_FACE, 'size':style.REPORT_GRAPH_FONT_SIZE})

        self.figure.patch.set_alpha(0.)
        self.plot.patch.set_alpha(0.)
    
    def save_image(self, filename, figsize=(512, 384), file_format='svg'):
        self.figure.set_figwidth(figsize[0]/80)
        self.figure.set_figheight(figsize[1]/80)
        self.plot_graph()
        with open(filename, 'wb') as fp:
            self.figure.savefig(fp, format=file_format, bbox_inches='tight')
    
    def get_embedded_html_image(self, figsize=(512, 384), file_format='svg'):
        self.figure.set_figwidth(figsize[0]/80)
        self.figure.set_figheight(figsize[1]/80)
        self.plot_graph()
        buf = BytesIO()
        self.figure.savefig(buf, format=file_format, bbox_inches='tight')
        data = base64.b64encode(buf.getbuffer()).decode("ascii")
        if file_format == 'svg':
            return f"<img src='data:image/svg+xml;base64,{data}'/>"
        elif file_format == 'png':
            return f"<img src='data:image/png;base64,{data}'/>"
        

