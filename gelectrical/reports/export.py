#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# export
#
#  Copyright 2020 Manu Varkey <manuvarkey@gmail.com>
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

"""Report and drawing exports of a project (moved from ``ProjectModel``, M2
step 9): pandapower HTML/JSON, element graph, report HTML/PDF (Jinja2 and
WeasyPrint) and drawing PDF (Cairo). No GTK imports."""

import logging, copy, datetime, io, math, os
from urllib.parse import urlsplit
from urllib.request import url2pathname
import cairo
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

# local files import
from ..core import constants, style
from ..core.fields import get_field_dict
from ..core.paths import abs_path, posix_path
from .tables import elements_to_table, fields_to_table
from .graph import GraphImage

# Get logger object
log = logging.getLogger(__name__)


def export_html_report(project, filename, call_at_exit=None):
    project.powermodel.export_html_report(filename)
    if call_at_exit:
        call_at_exit()

def export_element_graph(project, filename, call_at_exit=None):
    project.networkmodel.export_element_graph_html(filename)
    if call_at_exit:
        call_at_exit()
    
def export_json(project, filename, call_at_exit=None):
    project.powermodel.export_json(filename)
    if call_at_exit:
        call_at_exit()
    
def report_environment():
    """Jinja2 environment of the report templates. HTML templates are
    autoescaped (D10): user text is escaped unless the code marks it as
    generated markup with :class:`markupsafe.Markup`."""
    return Environment(loader=FileSystemLoader(abs_path("templates")),
                       autoescape=select_autoescape(enabled_extensions=('html',),
                                                    default_for_string=False))

def report_url_fetcher(allowed_files):
    """WeasyPrint URL fetcher that only resolves ``data:`` URLs and the
    given local files (D10): report content cannot reference other local
    files or network resources."""
    from weasyprint.urls import URLFetcher
    allowed = {os.path.realpath(path) for path in allowed_files}

    class ReportURLFetcher(URLFetcher):
        def fetch(self, url, headers=None):
            parts = urlsplit(url)
            scheme = parts.scheme.lower()
            if scheme == 'data':
                return super().fetch(url, headers)
            if scheme == 'file' and parts.netloc in ('', 'localhost'):
                if os.path.realpath(url2pathname(parts.path)) in allowed:
                    return super().fetch(url, headers)
            log.warning('report_url_fetcher - resource not allowed in report - ' + url[:200])
            raise ValueError('Resource not allowed in report: ' + url[:200])

    return ReportURLFetcher(allowed_protocols=('data', 'file'), allow_redirects=False)

def export_pdf_report(project, foldername, settings, call_at_exit=None):
    env = report_environment()
    
    # General variables
    project_settings = project.get_project_fields()
    report_settings = project.get_project_fields(page='Reports')
    export_graphs_flag = report_settings['export_graphs']['value']
    export_elements_flag = report_settings['export_elements']['value']
    export_boq_flag = report_settings['export_boq']['value']
    export_loadprofiles_flag = report_settings['export_loadprofiles']['value']
    export_ana_flag = report_settings['export_analysis']['value']
    gen_variables = {'program_version'        : 'v' + constants.PROGRAM_VER,
                     'project_name'           : project_settings['project_name']['value'],
                     'drawing_field_approved' : project_settings['drawing_field_approved']['value'],
                     'drawing_field_dept'     : project_settings['drawing_field_dept']['value'],
                     'drawing_field_address'  : escape(project_settings['drawing_field_address']['value']).replace('\n', Markup('</br>')),
                     'doc_title': project_settings['project_name']['value'],
                     'doc_author': project_settings['drawing_field_approved']['value'],
                     'doc_subject': "Project Report",
                     'doc_lang': project_settings['drawing_field_lang']['value'],
                     'doc_creator':constants.PROGRAM_NAME + ' v' + constants.PROGRAM_VER,
                     'doc_create_date': datetime.datetime.now().astimezone().replace(microsecond=0).isoformat(),
                     'doc_mod_date': datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()}
    
    # Elements
    element_captions = dict()
    element_refs = dict()
    element_tables = dict()
    element_lines = []
    element_loads = []
    element_switches = []
    element_nodes = dict()
    loadprofile_captions_used = set()
    project.networkmodel.setup_base_elements()
    base_elements = project.networkmodel.base_elements
    # First pass add all required elements
    for key, model in base_elements.items():
        if 'ref' in model.fields and model.code not in constants.NON_ELEMENT_CODES:
            element_captions[key] = model.fields['ref']['value'] + ' - ' + model.name
            element_refs[key] = model.fields['ref']['value']
            if export_elements_flag:
                element_tables[key] = fields_to_table(model.fields, insert_graph=export_graphs_flag)
        # Lines
        if model.code in constants.LINE_ELEMENT_CODES:
            element_lines.append(model)
        # Loads
        if model.code in constants.LOAD_ELEMENT_CODES:
            element_loads.append(model)
        # Switches
        if model.code in constants.SWITCH_ELEMENT_CODES:
            element_switches.append(model)
        # Nodes
        if model.code in constants.DISPLAY_ELEMENT_CODES:
            element_nodes[int(model.fields['ref']['value'])] = model
        # Loads
        if model.code in constants.LOADPROFILE_CODES and model.fields['load_profile']['value'] in project.loadprofiles:
            loadprofile_captions_used.add(model.fields['load_profile']['value'])

    # Second pass for adding assmebly details
    for key, model in base_elements.items():
        if model.code == 'element_assembly':
            assembly_fields = copy.deepcopy(model.fields)
            children_codes = model.children_codes
            children_list = []
            for child_code in children_codes:
                if child_code in element_refs:
                    child_ref = element_refs[child_code]
                    children_list.append(child_ref)
            children_str = ''
            for s in children_list:
                children_str = children_str + ', ' + s
            children_str = children_str[2:]
            assembly_fields['children'] = get_field_dict('str', 'Sub-elements', '', children_str, status_inactivate=False)
            # Add element
            element_captions[key] = model.fields['ref']['value'] + ' - ' + model.name
            element_refs[key] = model.fields['ref']['value']
            if export_elements_flag:
                element_tables[key] = fields_to_table(assembly_fields, insert_graph=export_graphs_flag)
    # Sort by reference
    element_captions = dict(sorted(element_captions.items(), key=lambda item:item[1]))
    if export_elements_flag:
        element_tables = {key:element_tables[key] for key in element_captions}
                             
    # BOQ
    boq_tables = dict()
    boq_captions = dict()
    E = constants.ELEMENT_FIELD
    R = constants.ELEMENT_RESULT
    P = constants.ELEMENT_PLACEHOLDER
    if export_boq_flag:
        # Lines
        if element_lines:
            col_codes = ['ref', 'name', 'designation', 'type', 'parallel', 'length_km', 'max_i_ka', 'df', 'in_service', 'loading_percent_max', 'pl_mw_max', 'pl_perc_max']
            col_captions = ['Reference', 'Name', 'Designation', 'Type', '# Parallel Lines',  'Length', 'Imax', 'Derating Factor', 'In Service ?', '% Loading', 'P loss', '% P loss']
            code_sources = [E,E,E,E,E,E,E,E,E,R,R,R]
            table = elements_to_table(element_lines, col_codes, col_captions, code_sources, 'boq_lines',
                                        show_element_class=True, sum_cols=[10])
            boq_tables['boq_lines'] = table
            boq_captions['boq_lines'] = 'Lines'
        # Loads
        if element_loads:

            def modifyfunc_load(table):
                table['Rated power'][0] = 'kVA'
                table['Sa'][0] = 'kVA'
                table['Sb'][0] = 'kVA'
                table['Sc'][0] = 'kVA'
                for slno, element in enumerate(element_loads):
                    scaling = element.fields['scaling']['value']
                    if element.code in ('element_load','element_async_motor_3ph'):
                        s_kva = round(element.fields['sn_kva']['value']*scaling, 4)
                        pf = str(round(element.fields['cos_phi']['value'], 2)) + (' lag' if element.fields['mode']['value'] else ' lead')
                    else:
                        fields = element.get_power_model('')[0][2]
                        p_a_kw = round(fields['p_a_mw']*1000*scaling, 4)
                        p_b_kw = round(fields['p_b_mw']*1000*scaling, 4)
                        p_c_kw = round(fields['p_c_mw']*1000*scaling, 4)
                        q_a_kvar = round(fields['q_a_mvar']*1000*scaling, 4)
                        q_b_kvar = round(fields['q_b_mvar']*1000*scaling, 4)
                        q_c_kvar = round(fields['q_c_mvar']*1000*scaling, 4)
                        p_kw = p_a_kw + p_b_kw + p_c_kw
                        q_kvar = q_a_kvar + q_b_kvar + q_c_kvar
                        table['Sa'][slno+1] = str(p_a_kw) + '+j' + str(q_a_kvar)
                        table['Sb'][slno+1] = str(p_b_kw) + '+j' + str(q_b_kvar)
                        table['Sc'][slno+1] = str(p_c_kw) + '+j' + str(q_c_kvar)
                        s_kva = round(math.sqrt(p_kw**2 + q_kvar**2), 4)
                        pf = str(round((p_kw/s_kva),2)) + (' lag' if q_kvar > 0 else ' lead')
                    table['Rated power'][slno+1] = str(s_kva)
                    table['PF'][slno+1] = pf
                    
            col_codes = ['ref', 'name', 'sn_kva', 'cos_phi', 'sa', 'sb', 'sc', 'in_service', 'load_profile']
            col_captions = ['Reference', 'Name', 'Rated power', 'PF', 'Sa', 'Sb', 'Sc', 'In Service ?', 'Load Profile']
            code_sources = [E,E,P,P,P,P,P,E,E]
            table = elements_to_table(element_loads, col_codes, col_captions, code_sources, 'boq_loads',
                                        show_element_class=True, modifyfunc=modifyfunc_load, sum_cols=[2])
            boq_tables['element_loads'] = table
            boq_captions['element_loads'] = 'Loads'
        # Switches
        if element_switches:

            def modifyfunc_switch(table):
                for slno, element in enumerate(element_switches):
                    if table['Line protection curve'][slno+1] == 'None':
                        table['Line protection curve'][slno+1] = ''
                    if table['Ground protection curve'][slno+1] == 'None':
                        table['Ground protection curve'][slno+1] = ''

            col_codes = ['ref', 'name', 'type', 'subtype', 'poles', 'Un', 'In', 
                        'prot_curve_type', 'prot_0_curve_type', 'closed']
            col_captions = ['Reference', 'Name', 'Type', 'Sub type', 'Poles', 'Un', 'In',
                            'Line protection curve', 'Ground protection curve', 'Closed']
            code_sources = [E,E,E,E,E,E,E,E,E,E]
            table = elements_to_table(element_switches, col_codes, col_captions, code_sources, 'boq_switches',
                                        show_element_class=False, modifyfunc=modifyfunc_switch)
            boq_tables['element_switches'] = table
            boq_captions['element_switches'] = 'Switches'
        # Nodes
        if element_nodes:
            nodes_sorted_by_name = [element_nodes[x] for x in sorted(element_nodes.keys())]
            col_codes = ['ref', 'vn_kv', 'delv_perc_max', 'ikss_ka_3ph_max', 'ikss_ka_3ph_min', 'ipss_ka_3ph_max', 'ikss_ka_1ph_max', 'ikss_ka_1ph_min']
            col_captions = ['Node ID', 'Vn', 'ΔV', 'Isc (sym, max)', 'Isc (sym, min)', 'Isc (pk, max)', 'Isc (L-G, max)', 'Isc (L-G, min)']
            code_sources = [E,R,R,R,R,R,R,R]
            table = elements_to_table(nodes_sorted_by_name, col_codes, col_captions, code_sources, 'boq_nodes',
                                        show_slno=False, show_element_class=False)
            boq_tables['element_nodes'] = table
            boq_captions['element_nodes'] = 'Nodes'
        
    # Load profiles
    loadprofile_captions = dict()
    loadprofile_images = dict()
    if export_loadprofiles_flag:
        loadprofile_captions = {key:project.loadprofiles[key][0] for key in loadprofile_captions_used}
        # Sort
        loadprofile_captions = dict(sorted(loadprofile_captions.items(), key=lambda item:item[1]))
        # Add images
        xlim = constants.GRAPH_LOAD_TIME_LIMITS
        ylim = constants.GRAPH_LOAD_CURRENT_LIMITS
        xlabel = 'Time (Hr)'
        ylabel = 'Diversity Factor'
        params = {}
        for loadprofile_caption in loadprofile_captions:
            title, graph_model = project.loadprofiles[loadprofile_caption]
            graph_image = GraphImage(xlim, ylim, '', xlabel, ylabel, graph_params=params)
            graph_image.add_plots(graph_model)
            emb_image = graph_image.get_embedded_html_image(figsize=(500, 175))
            loadprofile_images[loadprofile_caption] = emb_image
        
    # Analysis options
    if (settings['powerflow'] or settings['sc_sym'] or settings['sc_gf']) and export_ana_flag:
        analysis_flag = True
    else: 
        analysis_flag = False
    ana_opt_table = fields_to_table(project.get_project_fields(page='Simulation'))
    
    # Analysis results
    ana_res_captions = dict()
    ana_res_tables = dict()
    if analysis_flag: 
        base_elements = project.networkmodel.base_elements
        # First pass add all required elements
        for key, model in base_elements.items():
            if 'ref' in model.fields and (model.code not in constants.REFERENCE_CODES) and (model.code != 'element_assembly'):
                if model.res_fields:
                    table = fields_to_table(model.res_fields, insert_graph=export_graphs_flag)
                    ana_res_captions[str(key)+'_res'] = model.fields['ref']['value'] + ' - ' + model.name
                    ana_res_tables[str(key)+'_res'] = table
        # Sort by reference
        ana_res_captions = dict(sorted(ana_res_captions.items(), key=lambda item:item[1]))
        ana_res_tables = {key:ana_res_tables[key] for key in ana_res_captions}
    
    # Load HTML file    
    template = env.get_template("report.html")
    # Generated HTML (tables, embedded images) is markup; captions and
    # project text are escaped by the template (D10)
    element_tables = {key: Markup(value) for key, value in element_tables.items()}
    boq_tables = {key: Markup(value) for key, value in boq_tables.items()}
    loadprofile_images = {key: Markup(value) for key, value in loadprofile_images.items()}
    ana_opt_table = Markup(ana_opt_table)
    ana_res_tables = {key: Markup(value) for key, value in ana_res_tables.items()}
    template_vars = {'gen_variables': gen_variables,
                     'element_captions': element_captions,
                     'element_tables': element_tables,
                     'boq_tables': boq_tables,
                     'boq_captions': boq_captions,
                     'loadprofile_captions': loadprofile_captions,
                     'loadprofile_images': loadprofile_images,
                     'analysis_flag': analysis_flag,
                     'export_elements_flag': export_elements_flag,
                     'export_boq_flag': export_boq_flag,
                     'export_loadprofiles_flag': export_loadprofiles_flag,
                     'ana_opt_table': ana_opt_table,
                     'ana_res_tables': ana_res_tables,
                     'ana_res_captions': ana_res_captions
                    }
    html_out = template.render(template_vars)
    
    # Load CSS file
    template_css = env.get_template("report.css")
    template_vars_css = {'report_font': style.REPORT_FONT_FACE,
                         'report_font_size': style.REPORT_FONT_SIZE}
    css_out = template_css.render(template_vars_css)
    css_obj = io.BytesIO(bytes(css_out, 'utf-8'))
    
    # Render HTML, PDF
    filename_pdf = posix_path(foldername, 'report.pdf')
    filename_html = posix_path(foldername, 'report.html')
    filename_css = posix_path(foldername, 'report.css')
    with open(filename_html, 'w', encoding='utf-8') as fp:
        fp.write(html_out)
    with open(filename_css, 'w', encoding='utf-8') as fp:
        fp.write(css_out)
    from weasyprint import HTML
    url_fetcher = report_url_fetcher([filename_css])
    HTML(string=html_out, base_url=foldername, url_fetcher=url_fetcher).write_pdf(
        filename_pdf, stylesheets=[css_obj])
    
    if call_at_exit:
        call_at_exit()
    
def export_drawing(project, filename, call_at_exit=None):
    surface = cairo.PDFSurface(filename, 0, 0)
    proj_fields = project.get_project_fields()
    surface.set_metadata(cairo.PDFMetadata.TITLE, proj_fields['project_name']['value'])
    surface.set_metadata(cairo.PDFMetadata.AUTHOR, proj_fields['drawing_field_approved']['value'])
    surface.set_metadata(cairo.PDFMetadata.SUBJECT, 'Electrical Schematic Drawing')
    surface.set_metadata(cairo.PDFMetadata.CREATOR, constants.PROGRAM_NAME + ' v' + constants.PROGRAM_VER)
    surface.set_metadata(cairo.PDFMetadata.CREATE_DATE, datetime.datetime.now().astimezone().replace(microsecond=0).isoformat())
    surface.set_metadata(cairo.PDFMetadata.MOD_DATE, datetime.datetime.now().astimezone().replace(microsecond=0).isoformat())
    context = cairo.Context(surface)
    # If dark mode, load correct values while drawing
    dark_mode = style.check_dark_mode()
    if dark_mode:
        style.reset_dark_mode_drawing_values()
    for drawing_model in project.drawing_models:
        surface.set_size(drawing_model.fields['page_width']['value'], drawing_model.fields['page_height']['value'])
        drawing_model.export_drawing(context)
        surface.show_page()
    # If dark mode, restore original values
    if dark_mode:
        style.set_dark_mode_drawing_values()  
    surface.finish()
    if call_at_exit:
        call_at_exit()
    
def print_drawing(project, context, page_nr):
    if page_nr < len(project.drawing_models):
        drawing_model = project.drawing_models[page_nr]
        drawing_model.export_drawing(context)
