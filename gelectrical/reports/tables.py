#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# tables
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

"""HTML tables for reports: element fields, results and parameter
comparison tables. No GUI imports (graphs use Matplotlib without a GUI
backend through :mod:`gelectrical.reports.graph`)."""

import base64
import pandas as pd

from ..core import paths
from ..core.constants import ELEMENT_FIELD, ELEMENT_RESULT, ELEMENT_PLACEHOLDER
from ..core.fields import get_fields_from_params


def clean_markup(text):
    """Clear markup text of special characters"""
    for splchar, replspelchar in zip(['&', '<', '>', ], ['&amp;', '&lt;', '&gt;']):
        text = text.replace(splchar, replspelchar)
    return text

def elements_to_table(elements, col_codes, col_captions, code_sources, table_class=None, 
                      show_slno=True, show_element_class=True, modifyfunc=None, sum_cols=None):
    table = dict()
    clean = lambda x: clean_markup(str(x)).replace('\n','</br>')
    # Add unit line
    if show_slno:
        table['Sl.No.'] = ['']
    for col_caption in col_captions:
        table[col_caption] = ['']
    if show_element_class:
        table['Item Class'] = ['']
    # Add elements
    index = 1
    for element in elements:
        if show_slno:
            table['Sl.No.'].append(index)
        if show_element_class:
            table['Item Class'].append(element.name)
        for col_code, col_caption, code_source in zip(col_codes, col_captions, code_sources):
            # Select table
            if code_source == ELEMENT_FIELD:
                fields = element.fields
            elif code_source == ELEMENT_RESULT:
                fields = element.res_fields
            else:
                table[col_caption].append('')
                continue
            # Set value
            if col_code in fields:
                field = fields[col_code]
                table[col_caption][0] = field['unit']
                if field['type'] == 'graph':
                    if field['selection_list']:
                        table[col_caption].append(field['selection_list'][field['value']][0])
                    else:
                        table[col_caption].append(clean(field['value'][0]))
                elif field['type'] == 'float':
                    table[col_caption].append(str(round(field['value'], field['decimal'])))
                else:
                    table[col_caption].append(clean(field['value']))
            else:
                table[col_caption].append('')
        index += 1
    if modifyfunc:
        modifyfunc(table)
    if sum_cols:
        for index in sum_cols:
            # Get sum
            def float_conv(value):
                try:  # try evaluating float
                    return float(value)
                except:
                    return 0
                
            sum_of_col = sum(map(float_conv, table[col_captions[index]][1:])) # Ignore unit row
            # Add blank row
            if show_slno:
                table['Sl.No.'].append('&Sigma;')
            for col_caption in col_captions:
                table[col_caption].append('')
            if show_element_class:
                table['Item Class'].append('')
            table[col_captions[index]][-1] = sum_of_col
            
    return pd.DataFrame(table).to_html(index=False, escape=False, classes=table_class)
    
def fields_to_table(fields, insert_image=True, insert_graph=True):
    table = {'Sl.No.':[], 'Description': [], 'Value': [], 'Unit': []}
    clean = lambda x: clean_markup(str(x)).replace('\n','</br>')
    index = 1
    for field in fields.values():
        if field['status_enable'] == True:
            if field['type'] not in ('graph', 'data', 'heading'):
                table['Sl.No.'].append(index)
                table['Description'].append(clean(field['caption']))
                table['Unit'].append(field['unit'])
                if field['type'] == 'float':
                    value = str(round(field['value'], field['decimal']))
                else:
                    value = clean(field['value'])
                if field['selection_list'] and field['selection_image_list'] and insert_image:
                    sel_index = field['selection_list'].index(field['value'])
                    image_path = field['selection_image_list'][sel_index]
                    if image_path:
                        image_file = paths.abs_path('icons', image_path)
                        data_uri = base64.b64encode(open(image_file, 'rb').read()).decode('utf-8')
                        img_tag = "<div class='parent flex-parent'><div class='child flex-left'><img class='img_table' src='data:image/svg+xml;base64,{0}'></div><div class='child flex-right'>{1}</div></div>".format(data_uri, value)
                        table['Value'].append(img_tag)
                    else:
                        table['Value'].append(value)
                else:
                    table['Value'].append(value)
                index += 1
            elif field['type'] == 'heading':
                table['Sl.No.'].append('')
                table['Description'].append('<b>' + clean(field['caption']) + '</b>')
                table['Unit'].append(field['unit'])
                table['Value'].append(clean(field['value']))
            elif field['type'] == 'data':
                table['Sl.No.'].append(index)
                table['Description'].append(clean(field['caption']))
                table['Unit'].append(field['unit'])
                img_tag = ''
                graph_fields = ''
                # Add graphimage
                if insert_graph:
                    from .graph import GraphImage
                    xlim, ylim, xlabel, ylabel, graph_params = field['graph_options']
                    title = field['value']['graph_model'][0]
                    graph_models = field['value']['graph_model'][1]
                    graph_image = GraphImage(xlim, ylim, title, xlabel, ylabel, graph_params)
                    graph_image.add_plots(graph_models)
                    img_tag = graph_image.get_embedded_html_image(figsize=(200, 200))
                # Add graph options
                param_fields = get_fields_from_params(field['value']['parameters'])
                for param_key, param_field in param_fields.items():
                    caption = param_field['caption']
                    unit = param_field['unit']
                    value = param_field['value']
                    status_enable = param_field['status_enable']
                    param_type = param_field['type']
                    if status_enable:
                        if param_type == 'heading':
                            graph_fields += '</br><b>' + clean(caption) + '</b>'
                        else:
                            graph_fields += '</br>' + clean(caption + ' : ' + str(value) + ' ' + unit)
                table['Value'].append(img_tag + graph_fields.lstrip('</br>'))
                index += 1
            else:
                table['Sl.No.'].append(index)
                table['Description'].append(clean(field['caption']))
                table['Unit'].append(field['unit'])
                if field['selection_list']:
                    table['Value'].append(field['selection_list'][field['value']][0])
                else:
                    title = field['value'][0]
                    if insert_graph:
                        from .graph import GraphImage
                        xlim, ylim, xlabel, ylabel, graph_params = field['graph_options']
                        graph_models = field['value'][1]
                        graph_image = GraphImage(xlim, ylim, title, xlabel, ylabel, graph_params)
                        graph_image.add_plots(graph_models)
                        img_tag = graph_image.get_embedded_html_image(figsize=(200, 200))
                        table['Value'].append(img_tag)
                    else:
                        table['Value'].append(clean(title))
                index += 1
    return pd.DataFrame(table).to_html(index=False, escape=False, classes='element_fields')
    
def params_to_table(fields_list, titles):
    """Return pandas table with comparison of field values"""

    def get_frame(fields, caption):
        table = {'REF':[], 'DESCRIPTION': [], 'UNIT': [], caption: []}
        for ref, field in fields.items():
            if field['status_enable'] == True:
                table['REF'].append(ref)
                table['DESCRIPTION'].append(field['caption'])
                table['UNIT'].append(field['unit'])
                if field['type'] == 'float':
                    value = str(round(field['value'], field['decimal']))
                else:
                    value = field['value']
                table[caption].append(value)
        return pd.DataFrame(table)
    
    table_combined = None
    for fields, title in zip(fields_list, titles):
        table = get_frame(fields, title)
        if table_combined is not None:
            table_combined = pd.merge(table_combined, table, how='outer')
        else:
            table_combined = table
    columns = ['REF', 'DESCRIPTION', 'UNIT', *titles]
    return table_combined[columns]
    
