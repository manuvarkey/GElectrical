#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 ViviBeri contributors
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for read-only Pandapower JSON import helpers."""

import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from gelectrical.model.pandapower_import import get_network_summary, load_network_json


class TestPandapowerImport(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_file.write(b'{"pandapowerNet": {}}')
        self.temp_file.close()

    def tearDown(self):
        os.unlink(self.temp_file.name)

    def test_loads_network_with_pandapower(self):
        expected = {"bus": [1, 2], "line": [1]}
        fake_pandapower = types.SimpleNamespace(from_json=lambda filename: expected)
        with patch.dict(sys.modules, {"pandapower": fake_pandapower}):
            self.assertIs(load_network_json(self.temp_file.name), expected)

    def test_rejects_non_network_json(self):
        fake_pandapower = types.SimpleNamespace(from_json=lambda filename: {"name": "not a network"})
        with patch.dict(sys.modules, {"pandapower": fake_pandapower}):
            with self.assertRaisesRegex(ValueError, "valid pandapower network"):
                load_network_json(self.temp_file.name)

    def test_wraps_pandapower_parse_error(self):
        def fail_to_load(filename):
            raise RuntimeError("invalid JSON payload")

        fake_pandapower = types.SimpleNamespace(from_json=fail_to_load)
        with patch.dict(sys.modules, {"pandapower": fake_pandapower}):
            with self.assertRaisesRegex(ValueError, "could not read"):
                load_network_json(self.temp_file.name)

    def test_rejects_missing_and_empty_files(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            load_network_json(self.temp_file.name + ".missing")

        with open(self.temp_file.name, "wb"):
            pass

        with self.assertRaisesRegex(ValueError, "empty"):
            load_network_json(self.temp_file.name)

    def test_summarizes_populated_element_tables(self):
        network = {
            "bus": [1, 2, 3],
            "line": [1, 2],
            "load": [1],
            "ext_grid": [],
        }
        self.assertEqual(
            get_network_summary(network),
            [("Buses", 3), ("Lines", 2), ("Loads", 1)],
        )

    def test_summary_rejects_invalid_network(self):
        with self.assertRaisesRegex(ValueError, "valid pandapower network"):
            get_network_summary({"name": "invalid"})


if __name__ == "__main__":
    unittest.main()
