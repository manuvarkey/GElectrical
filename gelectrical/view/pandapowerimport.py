"""Read-only GTK viewer for imported Pandapower networks."""

from gi.repository import Gtk

from ..model.pandapower_import import (
    NETWORK_TABLES,
    run_imported_powerflow,
    summarize_network,
)


MAX_DISPLAY_ROWS = 1000
RESULT_TABLES = (
    ("res_bus", "Bus results"),
    ("res_line", "Line results"),
    ("res_trafo", "Transformer results"),
    ("res_trafo3w", "Three-winding transformer results"),
    ("res_load", "Load results"),
    ("res_sgen", "Static generator results"),
    ("res_gen", "Generator results"),
    ("res_ext_grid", "External grid results"),
)


def create_pandapower_json_file_chooser(parent):
    """Create the GTK 3 file chooser used to select a Pandapower JSON file."""
    file_filter = Gtk.FileFilter()
    file_filter.set_name("Pandapower JSON network")
    file_filter.add_pattern("*.json")
    file_filter.add_pattern("*.JSON")
    open_dialog = Gtk.FileChooserDialog(
        title="Import Pandapower JSON network",
        parent=parent,
        action=Gtk.FileChooserAction.OPEN,
    )
    open_dialog.add_buttons(
        "Cancel", Gtk.ResponseType.CANCEL,
        "Import", Gtk.ResponseType.ACCEPT,
    )
    open_dialog.set_local_only(True)
    open_dialog.set_modal(True)
    open_dialog.set_filter(file_filter)
    return open_dialog


class PandapowerImportDialog:
    """Display imported Pandapower tables and balanced power-flow results."""

    def __init__(self, parent, network, filename):
        self.network = network
        self.result_pages = {}
        self.dialog = Gtk.Dialog(
            title="Imported Pandapower Network",
            transient_for=parent,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        )
        self.dialog.set_default_size(1050, 680)
        self.dialog.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)

        content = self.dialog.get_content_area()
        content.set_spacing(8)
        content.set_border_width(10)

        heading = Gtk.Label()
        heading.set_markup("<b>{}</b>".format(GLibMarkup.escape(filename)))
        heading.set_xalign(0)
        content.pack_start(heading, False, False, 0)

        summary = Gtk.Label(label=summarize_network(network))
        summary.set_xalign(0)
        summary.set_selectable(True)
        content.pack_start(summary, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        content.pack_start(self.notebook, True, True, 0)

        for table_name, label in NETWORK_TABLES:
            table = network.get(table_name)
            if table is None or len(table.index) == 0:
                continue
            page, count = self._build_table_page(table)
            tab_label = Gtk.Label(label="{} ({})".format(label, len(table.index)))
            self.notebook.append_page(page, tab_label)
            if len(table.index) > count:
                page.set_tooltip_text(
                    "Showing the first {} of {} rows.".format(count, len(table.index)))

        if self.notebook.get_n_pages() == 0:
            empty = Gtk.Label(label="No supported network elements were found.")
            empty.set_margin_top(24)
            self.notebook.append_page(empty, Gtk.Label(label="Network"))

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.run_button = Gtk.Button(label="Run Balanced Power Flow")
        self.run_button.connect("clicked", self._on_run_powerflow)
        controls.pack_start(self.run_button, False, False, 0)

        self.status = Gtk.Label(label="Imported network is read-only; calculations do not modify the source project.")
        self.status.set_xalign(0)
        self.status.set_line_wrap(True)
        controls.pack_start(self.status, True, True, 0)
        content.pack_start(controls, False, False, 0)

        self.dialog.show_all()

    def _build_table_page(self, table):
        columns = [str(column) for column in table.columns]
        model = Gtk.ListStore(*([str] * (len(columns) + 1)))
        display_table = table.head(MAX_DISPLAY_ROWS)

        for index, row in display_table.iterrows():
            values = [str(index)]
            for value in row.tolist():
                if value is None:
                    values.append("")
                else:
                    try:
                        values.append("" if value != value else str(value))
                    except Exception:
                        values.append(str(value))
            model.append(values)

        tree = Gtk.TreeView(model=model)
        tree.set_enable_search(True)
        tree.set_search_column(0)
        tree.set_rules_hint(True)

        index_renderer = Gtk.CellRendererText()
        index_column = Gtk.TreeViewColumn("Index", index_renderer, text=0)
        index_column.set_resizable(True)
        index_column.set_min_width(70)
        tree.append_column(index_column)

        for position, title in enumerate(columns, start=1):
            renderer = Gtk.CellRendererText()
            renderer.set_property("ellipsize", 3)
            column = Gtk.TreeViewColumn(title, renderer, text=position)
            column.set_resizable(True)
            column.set_min_width(100)
            tree.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(tree)
        return scrolled, len(display_table)

    def _on_run_powerflow(self, _button):
        self.run_button.set_sensitive(False)
        self.status.set_text("Running balanced AC power flow...")
        while Gtk.events_pending():
            Gtk.main_iteration()

        try:
            run_imported_powerflow(self.network)
            self._show_powerflow_results()
            self.status.set_text("Power flow converged. Result tables are available in the Results tabs.")
        except Exception as error:
            self.status.set_text("Power flow failed: {}".format(error))
        finally:
            self.run_button.set_sensitive(True)

    def _show_powerflow_results(self):
        for table_name, label in RESULT_TABLES:
            table = self.network.get(table_name)
            if table is None or len(table.index) == 0:
                continue

            page, count = self._build_table_page(table)
            if table_name in self.result_pages:
                page_number = self.notebook.page_num(self.result_pages[table_name])
                if page_number >= 0:
                    self.notebook.remove_page(page_number)

            tab_label = Gtk.Label(label="{} ({})".format(label, len(table.index)))
            self.notebook.append_page(page, tab_label)
            self.result_pages[table_name] = page
            if len(table.index) > count:
                page.set_tooltip_text(
                    "Showing the first {} of {} rows.".format(count, len(table.index)))

        self.notebook.show_all()
        if self.result_pages:
            first_result = next(iter(self.result_pages.values()))
            self.notebook.set_current_page(self.notebook.page_num(first_result))

    def run(self):
        try:
            return self.dialog.run()
        finally:
            self.dialog.destroy()


class GLibMarkup:
    """Minimal markup escaping for labels populated from file names."""

    @staticmethod
    def escape(value):
        return (str(value).replace("&", "&amp;")
                .replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;").replace("'", "&apos;"))
