"""Headless GTK smoke tests for the Pandapower import dialog."""

import importlib
import os
import sys
import types
import unittest
from unittest.mock import patch

os.environ.setdefault("GDK_BACKEND", "x11")

try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
except (ImportError, ValueError):
    Gtk = None


@unittest.skipIf(Gtk is None, "GTK 3 introspection bindings are unavailable")
class PandapowerImportGtkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pandas as pd

        package = types.ModuleType("gelectrical")
        package.__path__ = [os.path.abspath("gelectrical")]
        sys.modules.setdefault("gelectrical", package)
        model_package = types.ModuleType("gelectrical.model")
        model_package.__path__ = [os.path.abspath("gelectrical/model")]
        sys.modules.setdefault("gelectrical.model", model_package)
        view_package = types.ModuleType("gelectrical.view")
        view_package.__path__ = [os.path.abspath("gelectrical/view")]
        sys.modules.setdefault("gelectrical.view", view_package)

        cls.module = importlib.import_module("gelectrical.view.pandapowerimport")
        cls.pd = pd

    def setUp(self):
        self.network = {
            "bus": self.pd.DataFrame({"vn_kv": [0.4], "name": ["Bus A"]}),
            "line": self.pd.DataFrame({"length_km": [1.0]}),
            "res_bus": self.pd.DataFrame({"vm_pu": [1.0], "va_degree": [0.0]}),
            "res_line": self.pd.DataFrame({"loading_percent": [12.5]}),
        }

    def test_file_chooser_uses_supported_gtk3_open_dialog(self):
        chooser = self.module.create_pandapower_json_file_chooser(None)
        try:
            self.assertEqual(chooser.get_action(), Gtk.FileChooserAction.OPEN)
            self.assertTrue(chooser.get_local_only())
            self.assertIsNotNone(chooser.get_filter())
            self.assertEqual(chooser.get_title(), "Import Pandapower JSON network")
        finally:
            chooser.destroy()

    def test_dialog_builds_network_tables_and_powerflow_control(self):
        dialog = self.module.PandapowerImportDialog(None, self.network, "sample.json")
        try:
            self.assertEqual(dialog.notebook.get_n_pages(), 2)
            self.assertEqual(dialog.run_button.get_label(), "Run Balanced Power Flow")
            self.assertTrue(dialog.run_button.get_sensitive())
            self.assertIn("Buses: 1", self.module.summarize_network(self.network))
        finally:
            dialog.dialog.destroy()

    def test_result_tables_are_added_and_refreshable(self):
        dialog = self.module.PandapowerImportDialog(None, self.network, "sample.json")
        try:
            dialog._show_powerflow_results()
            self.assertEqual(dialog.notebook.get_n_pages(), 4)
            first_pages = dict(dialog.result_pages)
            dialog._show_powerflow_results()
            self.assertEqual(dialog.notebook.get_n_pages(), 4)
            self.assertEqual(set(dialog.result_pages), set(first_pages))
        finally:
            dialog.dialog.destroy()

    def test_powerflow_button_runs_solver_and_displays_results(self):
        dialog = self.module.PandapowerImportDialog(None, self.network, "sample.json")
        try:
            with patch.object(self.module, "run_imported_powerflow", return_value=self.network) as runner:
                dialog.run_button.emit("clicked")
            runner.assert_called_once_with(self.network)
            self.assertIn("Power flow converged", dialog.status.get_text())
            self.assertEqual(self.notebook_page_labels(dialog), 4)
        finally:
            dialog.dialog.destroy()

    def test_powerflow_failure_is_reported_in_dialog(self):
        dialog = self.module.PandapowerImportDialog(None, self.network, "sample.json")
        try:
            with patch.object(self.module, "run_imported_powerflow", side_effect=ValueError("No slack source")):
                dialog.run_button.emit("clicked")
            self.assertIn("Power flow failed: No slack source", dialog.status.get_text())
            self.assertTrue(dialog.run_button.get_sensitive())
        finally:
            dialog.dialog.destroy()

    @staticmethod
    def notebook_page_labels(dialog):
        return dialog.notebook.get_n_pages()

    def test_filename_markup_is_escaped(self):
        self.assertEqual(
            self.module.GLibMarkup.escape("network<&>.json"),
            "network&lt;&amp;&gt;.json",
        )


if __name__ == "__main__":
    unittest.main()
