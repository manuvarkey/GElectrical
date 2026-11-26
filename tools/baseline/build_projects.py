#!/usr/bin/env python3
"""Build the regression coverage projects in ``tests/projects/``.

Milestone M1. The projects are scripted through the legacy model API (the
same element classes, ``set_text_field_value`` and ``insert_element_at_index``
calls the GTK editor uses) and saved with ``MainWindow.on_save``. Re-running
this script regenerates them; the committed ``.gepro`` files are the inputs
of the baseline, so regenerate only on purpose and re-capture afterwards.

Usage::

    xvfb-run -a pixi run -e test build-test-projects          # all
    xvfb-run -a pixi run -e test build-test-projects cov_trafo3w

Coordinates are drawing units (points); ``misc.M`` (8) is the port grid.
Connections are made by coinciding port coordinates or by ``Wire`` elements
(only the first and last wire points are ports).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import legacy  # noqa: E402

OUT = os.path.join(ROOT, 'tests', 'projects')

DAY_PROFILE = ['Day shift', [{'mode': 1, 'title': 'Day shift',
                              'xval': [0, 6, 8, 12, 13, 18, 20, 23],
                              'yval': [0.2, 0.2, 1.0, 1.0, 0.6, 1.0, 0.3, 0.2]}]]
NIGHT_PROFILE = ['Night', [{'mode': 1, 'title': 'Night',
                            'xval': [0, 5, 7, 19, 21, 23],
                            'yval': [1.0, 1.0, 0.3, 0.3, 1.0, 1.0]}]]


def render(target):
    """Draw an element or drawing model on a scratch surface (as the editor does)."""
    import cairo
    context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_RGB24, 16, 16))
    if hasattr(target, 'draw_model'):
        target.draw_model(context)
    else:
        target.draw(context)


class Builder:
    """Places legacy elements on the sheets of one legacy project."""

    def __init__(self, session):
        self.s = session
        self.project = session.project
        self.misc = session.misc
        self.M = self.misc.M
        self.registry = self.project.program_state['element_models']
        self.page = 0

    # -- project level -----------------------------------------------------

    def set_sim(self, **values):
        sim = self.project.get_project_fields(page='Simulation')
        for key, value in values.items():
            sim[key]['value'] = value

    def set_info(self, name):
        self.project.get_project_fields(page='Information')['project_name']['value'] = name

    def add_loadprofile(self, uid, profile):
        self.project.loadprofiles[uid] = profile

    def new_sheet(self):
        self.project.append_page()
        self.page = len(self.project.drawing_models) - 1
        return self.page

    def sheet_fields(self, **values):
        dm = self.project.drawing_models[self.page]
        for key, value in values.items():
            dm.fields[key]['value'] = value
        dm.update_title_block()

    @property
    def dm(self):
        return self.project.drawing_models[self.page]

    # -- elements ----------------------------------------------------------

    def make(self, code, **fields):
        cls = self.registry[code]
        element = cls(project_settings=self.project.program_state['project_settings'])
        if code in self.misc.LOADPROFILE_CODES:
            element.fields['load_profile']['selection_list'] = self.project.loadprofiles
        for key, value in fields.items():
            if key not in element.fields:
                raise KeyError('%s has no field %s' % (code, key))
            element.set_text_field_value(key, value)
        render(element)  # the editor draws the floating model: ports/extents update
        return element

    def place(self, code, at, port=0, **fields):
        """Insert ``code`` so that its port ``port`` is at drawing point ``at``."""
        element = self.make(code, **fields)
        px, py = element.ports[port]
        element.x = int(at[0] - px * self.M)
        element.y = int(at[1] - py * self.M)
        return self.insert(element)

    def insert(self, element):
        """Insert like ``make_floating_model_permenant``: a gid-stamped copy."""
        copy = self.dm.get_element_copy(element)
        if copy.code in self.misc.LOADPROFILE_CODES:
            copy.fields['load_profile']['selection_list'] = self.project.loadprofiles
        self.dm.insert_element_at_index(copy)
        return copy

    def place_xy(self, code, x, y, **fields):
        element = self.make(code, **fields)
        element.x, element.y = int(x), int(y)
        return self.insert(element)

    def ports(self, element):
        return [tuple(p) for p in element.get_ports_global()]

    def chain(self, at, specs):
        """Stack two-port elements downward from ``at``; return (end, elements)."""
        elements = []
        point = at
        for code, fields in specs:
            element = self.place(code, point, 0, **fields)
            elements.append(element)
            point = self.ports(element)[-1]
        return point, elements

    def wire(self, *points):
        Wire = self._wire_class()
        element = Wire(points=[tuple(int(v) for v in p) for p in points])
        self.dm.insert_element_at_index(element)  # editor wires carry no gid
        return element

    def _wire_class(self):
        from gelectrical.elementmodel.wire import Wire
        return Wire

    def bus(self, at, n_top=1, n_btm=3, width=12, **fields):
        """Bus bar with its first top port at ``at``; returns (bus, top, bottom)."""
        element = self.place('element_busbar', at, 0, n_top=n_top, n_btm=n_btm,
                             width=width, **fields)
        ports = self.ports(element)
        return element, ports[:n_top], ports[n_top:]

    def source(self, code, at, **fields):
        """Single-port source whose (bottom) port is at ``at``."""
        return self.place(code, at, 0, **fields)

    def text(self, x, y, text):
        element = self.place_xy('element_display_text', x, y)
        element.set_text_field_value('text', text)
        return element

    def assembly(self, elements, name, text1=''):
        """Group ``elements`` of the current sheet like the editor's Assembly tool."""
        render(self.dm)  # computes element extents
        self.dm.deselect_all()
        for element in elements:
            element.set_selection(True)
        self.dm.add_assembly_from_selection()
        self.dm.deselect_all()
        assembly = self.dm.elements[-1]
        assembly.fields['name']['value'] = name
        assembly.fields['text1']['value'] = text1
        return assembly


# ---------------------------------------------------------------------------
# Coverage projects
# ---------------------------------------------------------------------------

def cov_radial_lv(b):
    """MV grid, 2-winding transformer, LV board with every line and protection type."""
    b.set_info('COVERAGE RADIAL LV')
    b.set_sim(pf_method='Power flow', power_flow_3ph=False)
    grid = b.source('element_grid', (480, 96), ref='G1', vn_kv=11, s_sc_max_mva=250,
                    s_sc_min_mva=150)
    end, _ = b.chain(b.ports(grid)[0], [
        ('element_switch', {'ref': 'Q0'}),
        ('element_transformer', {'ref': 'T1', 'sn_mva': 0.5, 'vn_hv_kv': 11,
                                 'vn_lv_kv': 0.415, 'vk_percent': 5, 'vkr_percent': 1.2}),
    ])
    _, _, bottom = b.bus(end, n_btm=6, width=14, ref='B1', In=1000, Isc=36)
    feeders = [
        [('element_circuitbreaker', {'ref': 'Q1', 'In': 40}),
         ('element_line_cable', {'ref': 'W1', 'length_km': 0.05}),
         ('element_load', {'ref': 'X1', 'sn_kva': 15, 'cos_phi': 0.9})],
        [('element_fuse', {'ref': 'Q2', 'In': 63}),
         ('element_line_custom', {'ref': 'W2', 'length_km': 0.2}),
         ('element_load', {'ref': 'X2', 'sn_kva': 20, 'cos_phi': 0.85})],
        [('element_circuitbreaker', {'ref': 'Q3', 'In': 63}),
         ('element_line_bus', {'ref': 'W3', 'length_km': 0.03}),
         ('element_load', {'ref': 'X3', 'sn_kva': 30, 'cos_phi': 0.8})],
        [('element_contactor', {'ref': 'K4', 'In': 16}),
         ('element_line', {'ref': 'W4', 'length_km': 0.04}),
         ('element_async_motor_3ph', {'ref': 'M4', 'p_kw': 5.5})],
        [('element_circuitbreaker', {'ref': 'Q5', 'In': 16}),
         ('element_line_cable', {'ref': 'W5', 'length_km': 0.06}),
         ('element_single_phase_load', {'ref': 'X5', 'sn_kva': 3, 'phase': 'B'})],
        [('element_circuitbreaker', {'ref': 'Q6', 'In': 10}),
         ('element_line_cable', {'ref': 'W6', 'length_km': 0.02}),
         ('element_async_motor_1ph', {'ref': 'M6', 'p_kw': 1.1, 'phase': 'C'})],
    ]
    for port, specs in zip(bottom, feeders):
        b.chain(port, specs)
    b.text(800, 80, 'Coverage project: radial LV distribution.\nAll line and protection types.')


def cov_generation(b):
    """LV grid with synchronous and static generation; time series, balanced.

    The legacy 3-phase power flow fails with a synchronous generator
    (KeyError 'res_gen_3ph'); ``cov_static_generation`` covers 3-phase.
    """
    b.set_info('COVERAGE GENERATION')
    b.set_sim(pf_method='Time series', power_flow_3ph=False)
    b.add_loadprofile('prof_day', DAY_PROFILE)
    b.add_loadprofile('prof_night', NIGHT_PROFILE)
    _, top, bottom = b.bus((240, 200), n_top=4, n_btm=4, width=16, ref='B1', In=800, Isc=25)
    b.source('element_grid', top[0], ref='G1', vn_kv=0.415, s_sc_max_mva=20, s_sc_min_mva=10)
    b.source('element_generator', top[1], ref='G2', vn_kv=0.415, p_mw=0.05, sn_mva=0.0625)
    b.source('element_staticgenerator', top[2], ref='G3', p_mw=0.02, q_mvar=0.0)
    b.source('element_single_phase_staticgenerator', top[3], ref='G4', p_kw=3, phase='A')
    feeders = [
        [('element_circuitbreaker', {'ref': 'Q1', 'In': 63}),
         ('element_line_cable', {'ref': 'W1', 'length_km': 0.04}),
         ('element_load', {'ref': 'X1', 'sn_kva': 25, 'load_profile': 'prof_day'})],
        [('element_circuitbreaker', {'ref': 'Q2', 'In': 63}),
         ('element_line_cable', {'ref': 'W2', 'length_km': 0.05}),
         ('element_load', {'ref': 'X2', 'sn_kva': 20, 'load_profile': 'prof_night'})],
        [('element_circuitbreaker', {'ref': 'Q3', 'In': 32}),
         ('element_line_cable', {'ref': 'W3', 'length_km': 0.03}),
         ('element_single_phase_load', {'ref': 'X3', 'sn_kva': 4, 'phase': 'C',
                                        'load_profile': 'prof_day'})],
        [('element_circuitbreaker', {'ref': 'Q4', 'In': 25}),
         ('element_line_cable', {'ref': 'W4', 'length_km': 0.02}),
         ('element_load', {'ref': 'X4', 'sn_kva': 10, 'in_service': False})],
    ]
    for port, specs in zip(bottom, feeders):
        b.chain(port, specs)


def cov_static_generation(b):
    """Static generators (3-phase and 1-phase) only; time series, 3-phase."""
    b.set_info('COVERAGE STATIC GENERATION')
    b.set_sim(pf_method='Time series', power_flow_3ph=True)
    b.add_loadprofile('prof_day', DAY_PROFILE)
    _, top, bottom = b.bus((240, 200), n_top=3, n_btm=3, width=16, ref='B1', In=400, Isc=25)
    b.source('element_grid', top[0], ref='G1', vn_kv=0.415, s_sc_max_mva=20, s_sc_min_mva=10)
    b.source('element_staticgenerator', top[1], ref='G2', p_mw=0.015, q_mvar=0.002)
    b.source('element_single_phase_staticgenerator', top[2], ref='G3', p_kw=4, phase='B')
    b.chain(bottom[0], [('element_circuitbreaker', {'ref': 'Q1', 'In': 63}),
                        ('element_line_cable', {'ref': 'W1', 'length_km': 0.04}),
                        ('element_load', {'ref': 'X1', 'sn_kva': 20, 'load_profile': 'prof_day'})])
    b.chain(bottom[1], [('element_circuitbreaker', {'ref': 'Q2', 'In': 32}),
                        ('element_line_cable', {'ref': 'W2', 'length_km': 0.03}),
                        ('element_single_phase_load', {'ref': 'X2', 'sn_kva': 5, 'phase': 'A'})])
    b.chain(bottom[2], [('element_circuitbreaker', {'ref': 'Q3', 'In': 25}),
                        ('element_line_cable', {'ref': 'W3', 'length_km': 0.02}),
                        ('element_async_motor_3ph', {'ref': 'M3', 'p_kw': 3})])


def cov_impedance(b):
    """Series impedance and inductance elements; power flow, balanced."""
    b.set_info('COVERAGE IMPEDANCE')
    b.set_sim(pf_method='Power flow', power_flow_3ph=False)
    grid = b.source('element_grid', (400, 96), ref='G1', vn_kv=0.415, s_sc_max_mva=15,
                    s_sc_min_mva=8)
    _, _, bottom = b.bus(b.ports(grid)[0], n_btm=2, width=14, ref='B1', In=400, Isc=25)
    b.chain(bottom[0], [('element_impedance', {'ref': 'Z1', 'xft_pu': 0.02}),
                        ('element_load', {'ref': 'X1', 'sn_kva': 10})])
    b.chain(bottom[1], [('element_inductance', {'ref': 'L2'}),
                        ('element_load', {'ref': 'X2', 'sn_kva': 8})])


def cov_xward(b):
    """Extended ward equivalent; power flow, balanced."""
    b.set_info('COVERAGE XWARD')
    b.set_sim(pf_method='Power flow', power_flow_3ph=False)
    grid = b.source('element_grid', (400, 96), ref='G1', vn_kv=0.415, s_sc_max_mva=15,
                    s_sc_min_mva=8)
    _, _, bottom = b.bus(b.ports(grid)[0], n_btm=2, width=14, ref='B1', In=400, Isc=25)
    b.chain(bottom[0], [('element_circuitbreaker', {'ref': 'Q1', 'In': 32}),
                        ('element_xward', {'ref': 'X1', 'ps_mw': 0.004, 'qs_mvar': 0.001,
                                           'pz_mw': 0.001, 'qz_mvar': 0.0, 'r_ohm': 0.1,
                                           'x_ohm': 0.3, 'vm_pu': 1.0})])
    b.chain(bottom[1], [('element_circuitbreaker', {'ref': 'Q2', 'In': 32}),
                        ('element_load', {'ref': 'X2', 'sn_kva': 8})])


def cov_trafo3w(b):
    """110 kV grid with a three-winding transformer feeding two buses."""
    b.set_info('COVERAGE TRAFO3W')
    b.set_sim(pf_method='Power flow', power_flow_3ph=False)
    grid = b.source('element_grid', (520, 96), ref='G1', vn_kv=110, s_sc_max_mva=3000,
                    s_sc_min_mva=2000)
    end, (sw, t3) = b.chain(b.ports(grid)[0], [
        ('element_switch', {'ref': 'Q0'}),
        ('element_transformer3w', {'ref': 'T1'}),
    ])
    p_mv, p_lv = b.ports(t3)[1], b.ports(t3)[2]
    y_mid = p_mv[1] + 5 * b.M
    mv_at = (p_mv[0] - 25 * b.M, p_mv[1] + 10 * b.M)
    lv_at = (p_lv[0] + 25 * b.M, p_lv[1] + 10 * b.M)
    b.wire(p_mv, (p_mv[0], y_mid), (mv_at[0], y_mid), mv_at)
    b.wire(p_lv, (p_lv[0], y_mid), (lv_at[0], y_mid), lv_at)
    _, _, mv_bottom = b.bus(mv_at, n_btm=2, width=14, ref='B1', In=1250, Isc=25)
    _, _, lv_bottom = b.bus(lv_at, n_btm=2, width=14, ref='B2', In=1250, Isc=25)
    b.chain(mv_bottom[0], [('element_switch', {'ref': 'Q1'}),
                           ('element_load', {'ref': 'X1', 'sn_kva': 4000, 'cos_phi': 0.9})])
    b.chain(mv_bottom[1], [('element_switch', {'ref': 'Q2'}),
                           ('element_shunt_cap', {'ref': 'C2', 'q_kvar': -1000, 'vn_kv': 20})])
    b.chain(lv_bottom[0], [('element_switch', {'ref': 'Q3'}),
                           ('element_load', {'ref': 'X3', 'sn_kva': 3000, 'cos_phi': 0.85})])
    b.chain(lv_bottom[1], [('element_switch', {'ref': 'Q4'}),
                           ('element_shunt', {'ref': 'Z4', 'p_kw': 50, 'q_kvar': 0,
                                              'vn_kv': 10})])


def cov_advanced(b):
    """Shunts, wards, asymmetric load, change-over switch; power flow with diversity.

    Impedance and inductance are in ``cov_impedance`` because the legacy
    line-to-ground short circuit fails for them (KeyError 'gf0_pu'); the
    extended ward is in ``cov_xward`` because it makes the zero-sequence
    calculations fail (FloatingPointError in makeYbus).
    """
    b.set_info('COVERAGE ADVANCED')
    b.set_sim(pf_method='Power flow with diversity', power_flow_3ph=False)
    grid = b.source('element_grid', (560, 96), ref='G1', vn_kv=0.415,
                    s_sc_max_mva=15, s_sc_min_mva=8)
    _, _, bottom = b.bus(b.ports(grid)[0], n_btm=8, width=14, ref='B1', In=630, Isc=25,
                         DF=0.8)
    # Bus first top port is at the middle; bottom ports span both sides.
    b.chain(bottom[0], [('element_circuitbreaker', {'ref': 'Q1', 'In': 32}),
                        ('element_line_cable', {'ref': 'W1', 'length_km': 0.03}),
                        ('element_load', {'ref': 'X1', 'sn_kva': 10})])
    b.chain(bottom[1], [('element_fuse', {'ref': 'Q2', 'In': 32}),
                        ('element_line_cable', {'ref': 'W2', 'length_km': 0.02}),
                        ('element_single_phase_load', {'ref': 'X2', 'sn_kva': 3, 'phase': 'C'})])
    b.chain(bottom[2], [('element_circuitbreaker', {'ref': 'Q3', 'In': 32}),
                        ('element_shunt', {'ref': 'Z3', 'p_kw': 5})])
    b.chain(bottom[3], [('element_circuitbreaker', {'ref': 'Q4', 'In': 32}),
                        ('element_shunt_cap', {'ref': 'C4', 'q_kvar': -5})])
    b.chain(bottom[4], [('element_circuitbreaker', {'ref': 'Q5', 'In': 32}),
                        ('element_ward', {'ref': 'X5', 'ps_mw': 0.005, 'qs_mvar': 0.001,
                                          'pz_mw': 0.001, 'qz_mvar': 0.0005})])
    b.chain(bottom[5], [('element_switch', {'ref': 'Q6'}),
                        ('element_load', {'ref': 'X6', 'sn_kva': 4, 'mode': False})])
    b.chain(bottom[6], [('element_circuitbreaker', {'ref': 'Q7', 'In': 32}),
                        ('element_line_cable', {'ref': 'W7', 'length_km': 0.03}),
                        ('element_asymmetric_load', {'ref': 'X7', 'p_a_kw': 3, 'p_b_kw': 1,
                                                     'p_c_kw': 0.5, 'q_a_kvar': 1})])
    end, _ = b.chain(bottom[7], [('element_circuitbreaker', {'ref': 'Q8', 'In': 40})])
    co = b.place('element_co_switch', end, 0, ref='K8', position=1)
    out1, out2 = b.ports(co)[1], b.ports(co)[2]
    b.chain(out1, [('element_contactor', {'ref': 'K9', 'In': 16}),
                   ('element_async_motor_3ph', {'ref': 'M9', 'p_kw': 4})])
    x10_at = (out2[0] + 10 * b.M, out2[1] + 4 * b.M)
    b.wire(out2, (out2[0], out2[1] + 2 * b.M), (x10_at[0], out2[1] + 2 * b.M), x10_at)
    b.chain(x10_at, [('element_load', {'ref': 'X10', 'sn_kva': 6})])


def cov_multisheet(b):
    """Three sheets, cross references, assemblies, wires, earthing variants."""
    b.set_info('COVERAGE MULTISHEET')
    b.set_sim(pf_method='Time series', power_flow_3ph=False)
    b.add_loadprofile('prof_day', DAY_PROFILE)
    b.sheet_fields(name='Supply', title='SUPPLY')
    # Sheet 1: grid, transformer, TT bus (earthing resistance), feeders to references
    grid = b.source('element_grid', (400, 96), ref='G1', vn_kv=11, s_sc_max_mva=200,
                    s_sc_min_mva=100, r0x0_max=0.2, x0x_max=1.2)
    end, _ = b.chain(b.ports(grid)[0], [
        ('element_circuitbreaker', {'ref': 'Q0', 'In': 63}),
        ('element_transformer', {'ref': 'T1', 'sn_mva': 0.25, 'vector_group': 'Dyn'}),
    ])
    _, _, bottom = b.bus(end, n_btm=3, width=30, ref='B1', In=400, Isc=25, r_grid=10)
    e1, f1 = b.chain(bottom[0], [('element_circuitbreaker', {'ref': 'Q1', 'In': 63}),
                                 ('element_line_cable', {'ref': 'W1', 'length_km': 0.08})])
    b.place('element_reference', e1, 0, ref='CR1', sheet='2', title='TO SHEET 2')
    e2, _ = b.chain(bottom[1], [('element_circuitbreaker', {'ref': 'Q2', 'In': 40}),
                                ('element_line_cable', {'ref': 'W2', 'length_km': 0.05})])
    b.place('element_reference_box', e2, 0, ref='CR2', sheet='3', title='TO SHEET 3')
    # Local load through an L-shaped wire
    p = bottom[2]
    load_at = (p[0] + 12 * b.M, p[1] + 10 * b.M)
    b.wire(p, (p[0], p[1] + 5 * b.M), (load_at[0], p[1] + 5 * b.M), load_at)
    b.chain(load_at, [('element_load', {'ref': 'X1', 'sn_kva': 5, 'load_profile': 'prof_day'})])
    b.assembly(f1, 'FEEDER 1', 'Breaker and cable')
    b.text(760, 80, 'Supply sheet. B1 has an earthing resistance (TT system).')

    # Sheet 2: reference, distribution board with diversity, status cases
    b.new_sheet()
    b.sheet_fields(name='Board', title='DISTRIBUTION BOARD')
    ref = b.place('element_reference', (400, 96), 0, ref='CR1', sheet='1', title='FROM SHEET 1')
    end, _ = b.chain(b.ports(ref)[1], [('element_circuitbreaker', {'ref': 'Q11', 'In': 63})])
    _, _, bottom = b.bus(end, n_btm=3, width=16, ref='B2', In=250, Isc=16, DF=0.7)
    _, f11 = b.chain(bottom[0], [('element_circuitbreaker', {'ref': 'Q12', 'In': 32}),
                                 ('element_line_cable', {'ref': 'W12', 'length_km': 0.03}),
                                 ('element_load', {'ref': 'X12', 'sn_kva': 10})])
    b.chain(bottom[1], [('element_circuitbreaker', {'ref': 'Q13', 'In': 32}),
                        ('element_line_cable', {'ref': 'W13', 'length_km': 0.03,
                                                'in_service': False}),
                        ('element_load', {'ref': 'X13', 'sn_kva': 8})])
    b.chain(bottom[2], [('element_switch', {'ref': 'Q14', 'closed': False}),
                        ('element_line_cable', {'ref': 'W14', 'length_km': 0.02}),
                        ('element_load', {'ref': 'X14', 'sn_kva': 6, 'load_profile': 'prof_day'})])
    b.assembly(f11[:2], 'OUTGOING 1')

    # Sheet 3: reference box, IT-like bus (high earthing resistance)
    b.new_sheet()
    b.sheet_fields(name='Annex', title='ANNEX')
    refb = b.place('element_reference_box', (400, 96), 0, ref='CR2', sheet='1',
                   title='FROM SHEET 1')
    end, _ = b.chain(b.ports(refb)[1], [('element_line_cable', {'ref': 'W21',
                                                                'length_km': 0.01})])
    _, _, bottom = b.bus(end, n_btm=2, width=16, ref='B3', In=100, Isc=10, r_grid=100)
    b.chain(bottom[0], [('element_circuitbreaker', {'ref': 'Q22', 'In': 16}),
                        ('element_single_phase_load', {'ref': 'X22', 'sn_kva': 2, 'phase': 'A'})])
    b.chain(bottom[1], [('element_circuitbreaker', {'ref': 'Q23', 'In': 16}),
                        ('element_load', {'ref': 'X23', 'sn_kva': 4})])


# ---------------------------------------------------------------------------
# Edge projects
# ---------------------------------------------------------------------------

def edge_empty(b):
    """A new project saved without any element."""
    b.set_info('EDGE EMPTY')


def _simple_supply(b, x=400, n_btm=3, ref='B1'):
    grid = b.source('element_grid', (x, 96), ref='G1', vn_kv=0.415, s_sc_max_mva=10,
                    s_sc_min_mva=5)
    return b.bus(b.ports(grid)[0], n_btm=n_btm, width=14, ref=ref)


def edge_unconnected(b):
    """Unconnected ports: a dangling cable, a free load and a free bus port."""
    b.set_info('EDGE UNCONNECTED')
    _, _, bottom = _simple_supply(b)
    b.chain(bottom[0], [('element_line_cable', {'ref': 'W1', 'length_km': 0.02}),
                        ('element_load', {'ref': 'X1', 'sn_kva': 5})])
    b.chain(bottom[1], [('element_line_cable', {'ref': 'W2', 'length_km': 0.02})])
    b.place('element_load', (900, 400), 0, ref='X2', sn_kva=3)


def edge_islanded(b):
    """Second network island without a source."""
    b.set_info('EDGE ISLANDED')
    _, _, bottom = _simple_supply(b, n_btm=1)
    b.chain(bottom[0], [('element_line_cable', {'ref': 'W1', 'length_km': 0.02}),
                        ('element_load', {'ref': 'X1', 'sn_kva': 5})])
    _, _, bottom2 = b.bus((900, 200), n_btm=2, width=14, ref='B2')
    b.chain(bottom2[0], [('element_line_cable', {'ref': 'W2', 'length_km': 0.02}),
                         ('element_load', {'ref': 'X2', 'sn_kva': 5})])
    b.chain(bottom2[1], [('element_load', {'ref': 'X3', 'sn_kva': 2})])


def edge_missing_loadprofile(b):
    """Loads referencing a load profile that does not exist."""
    b.set_info('EDGE MISSING LOAD PROFILE')
    b.set_sim(pf_method='Time series', power_flow_3ph=False)
    _, _, bottom = _simple_supply(b, n_btm=2)
    _, (_, load) = b.chain(bottom[0], [('element_line_cable', {'ref': 'W1', 'length_km': 0.02}),
                                       ('element_load', {'ref': 'X1', 'sn_kva': 5})])
    load.fields['load_profile']['value'] = 'missing-profile-uid'
    _, (load2,) = b.chain(bottom[1], [('element_single_phase_load', {'ref': 'X2', 'sn_kva': 2})])
    load2.fields['load_profile']['value'] = 'missing-profile-uid'


def edge_unusual_values(b):
    """Zero, very small and very large values in otherwise valid elements."""
    b.set_info('EDGE UNUSUAL VALUES')
    b.set_sim(lv_tol_percent=10, r_fault_ohm=0.05, x_fault_ohm=0.01, show_impedances=True)
    grid = b.source('element_grid', (400, 96), ref='G1', vn_kv=11, s_sc_max_mva=1000,
                    s_sc_min_mva=50)
    end, _ = b.chain(b.ports(grid)[0], [
        ('element_transformer', {'ref': 'T1', 'sn_mva': 2.5, 'vk_percent': 6.25,
                                 'tap_pos': 4, 'vector_group': 'Dyn'}),
    ])
    _, _, bottom = b.bus(end, n_btm=4, width=14, ref='B1', In=4000, Isc=50, DF=0.5)
    b.chain(bottom[0], [('element_line_cable', {'ref': 'W1', 'length_km': 1e-4}),
                        ('element_load', {'ref': 'X1', 'sn_kva': 0})])
    b.chain(bottom[1], [('element_line_cable', {'ref': 'W2', 'length_km': 2.5, 'parallel': 4}),
                        ('element_load', {'ref': 'X2', 'sn_kva': 100, 'scaling': 0})])
    b.chain(bottom[2], [('element_line_cable', {'ref': 'W3', 'length_km': 0.1}),
                        ('element_load', {'ref': 'X3', 'sn_kva': 60, 'cos_phi': 1})])
    b.chain(bottom[3], [('element_circuitbreaker', {'ref': 'Q4', 'In': 6}),
                        ('element_load', {'ref': 'X4', 'sn_kva': 0.1, 'cos_phi': 0.1})])


def edge_many_sheets(b):
    """Six sheets chained by cross references."""
    b.set_info('EDGE MANY SHEETS')
    _, _, bottom = _simple_supply(b, n_btm=2)
    b.chain(bottom[0], [('element_load', {'ref': 'X1', 'sn_kva': 2})])
    end, _ = b.chain(bottom[1], [('element_line_cable', {'ref': 'W1', 'length_km': 0.01})])
    b.place('element_reference', end, 0, ref='CR1', sheet='2')
    for sheet in range(2, 7):
        b.new_sheet()
        b.sheet_fields(name='Sheet %d' % sheet)
        ref = b.place('element_reference', (400, 96), 0, ref='CR%d' % (sheet - 1),
                      sheet=str(sheet - 1))
        end, _ = b.chain(b.ports(ref)[1], [
            ('element_line_cable', {'ref': 'W%d' % sheet, 'length_km': 0.01})])
        _, _, bb = b.bus(end, n_btm=2, width=14, ref='B%d' % sheet)
        b.chain(bb[0], [('element_load', {'ref': 'X%d' % sheet, 'sn_kva': 2})])
        if sheet < 6:
            b.place('element_reference', bb[1], 0, ref='CR%d' % sheet, sheet=str(sheet + 1))


PROJECTS = {
    'cov_radial_lv': cov_radial_lv,
    'cov_generation': cov_generation,
    'cov_static_generation': cov_static_generation,
    'cov_trafo3w': cov_trafo3w,
    'cov_impedance': cov_impedance,
    'cov_xward': cov_xward,
    'cov_advanced': cov_advanced,
    'cov_multisheet': cov_multisheet,
    'edge/empty': edge_empty,
    'edge/unconnected': edge_unconnected,
    'edge/islanded': edge_islanded,
    'edge/missing_loadprofile': edge_missing_loadprofile,
    'edge/unusual_values': edge_unusual_values,
    'edge/many_sheets': edge_many_sheets,
}


def build(name):
    session = legacy.LegacySession()
    try:
        builder = Builder(session)
        # Fixed sheet metadata so files do not depend on the build date
        for drawing_model in session.project.drawing_models:
            drawing_model.fields['date_of_issue']['value'] = '2026-11-26'
        PROJECTS[name](builder)
        for drawing_model in session.project.drawing_models:
            drawing_model.fields['date_of_issue']['value'] = '2026-11-26'
            drawing_model.update_title_block()
            render(drawing_model)  # sheets are drawn before the user saves
        path = os.path.join(OUT, name + '.gepro')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        session.save(path)
        return path
    finally:
        session.close()


def main(argv):
    legacy.isolate_environment()
    legacy.import_legacy()
    names = argv or list(PROJECTS)
    for name in names:
        print('built', os.path.relpath(build(name), ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
