import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "gelectrical"
    / "model"
    / "pandapower_import.py"
)
SPEC = importlib.util.spec_from_file_location("pandapower_import", MODULE_PATH)
PANDAPOWER_IMPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PANDAPOWER_IMPORT)
summarize_network = PANDAPOWER_IMPORT.summarize_network
run_imported_powerflow = PANDAPOWER_IMPORT.run_imported_powerflow
validate_powerflow_slack = PANDAPOWER_IMPORT.validate_powerflow_slack
load_pandapower_json = PANDAPOWER_IMPORT.load_pandapower_json


class SummarizeNetworkTests(unittest.TestCase):
    def test_summarizes_populated_tables_and_ignores_empty_tables(self):
        network = {
            "bus": [1, 2, 3],
            "line": [1],
            "trafo": [],
            "load": [1, 2],
            "ext_grid": [1],
        }

        self.assertEqual(
            summarize_network(network),
            "Buses: 3\nLines: 1\nLoads: 2\nExternal grids: 1",
        )

    def test_handles_missing_tables(self):
        self.assertEqual(
            summarize_network({}),
            "The imported network contains no recognized elements.",
        )




class PowerFlowValidationTests(unittest.TestCase):
    class FakeTable:
        def __init__(self, rows):
            self.rows = rows

        def __len__(self):
            return len(self.rows)

        def iterrows(self):
            return enumerate(self.rows)

    class FakePandapower:
        def __init__(self):
            self.called_with = None

        def runpp(self, network, **kwargs):
            self.called_with = (network, kwargs)
            network["converged"] = True

    def test_accepts_in_service_external_grid(self):
        validate_powerflow_slack({
            "ext_grid": self.FakeTable([{"in_service": True}]),
            "gen": self.FakeTable([]),
        })

    def test_accepts_active_slack_generator(self):
        validate_powerflow_slack({
            "ext_grid": self.FakeTable([]),
            "gen": self.FakeTable([{"in_service": True, "slack": True}]),
        })

    def test_rejects_network_without_slack_source(self):
        with self.assertRaisesRegex(ValueError, "no in-service external grid"):
            validate_powerflow_slack({
                "ext_grid": self.FakeTable([]),
                "gen": self.FakeTable([{"in_service": True, "slack": False}]),
            })

    def test_ignores_out_of_service_external_grid(self):
        with self.assertRaises(ValueError):
            validate_powerflow_slack({
                "ext_grid": self.FakeTable([{"in_service": False}]),
                "gen": self.FakeTable([]),
            })

    def test_runs_powerflow_with_supported_options(self):
        network = {
            "ext_grid": self.FakeTable([{"in_service": True}]),
            "gen": self.FakeTable([]),
        }
        fake_pp = self.FakePandapower()

        result = run_imported_powerflow(network, pandapower_module=fake_pp)

        self.assertIs(result, network)
        self.assertTrue(network["converged"])
        self.assertEqual(
            fake_pp.called_with[1],
            {"run_control": True, "calculate_voltage_angles": True},
        )


class LoadPandapowerJsonTests(unittest.TestCase):
    class FakePandapower:
        def __init__(self):
            self.filename = None
            self.network = {"bus": [1]}

        def from_json(self, filename):
            self.filename = filename
            return self.network

    def test_loads_json_through_pandapower_and_returns_network(self):
        fake_pp = self.FakePandapower()

        network = load_pandapower_json("/tmp/sample.json", pandapower_module=fake_pp)

        self.assertEqual(fake_pp.filename, "/tmp/sample.json")
        self.assertIs(network, fake_pp.network)


if __name__ == "__main__":
    unittest.main()
