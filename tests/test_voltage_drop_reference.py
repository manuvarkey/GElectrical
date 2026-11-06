"""Reference regression test for the sample cable voltage-drop network.

Expected values are taken from the independently calculated comparison in
sample_files/cable_voltage_drop_test/calculations.ipynb.
"""

import cmath
import math
import unittest
from pathlib import Path

import pandapower as pp


SAMPLE_NETWORK = (
    Path(__file__).resolve().parents[1]
    / "sample_files"
    / "cable_voltage_drop_test"
    / "network.json"
)


class VoltageDropReferenceTest(unittest.TestCase):
    def test_sample_network_voltage_drop_matches_reference(self):
        network = pp.from_json(str(SAMPLE_NETWORK))
        pp.runpp(network, calculate_voltage_angles=True)

        source_voltage = cmath.rect(
            network.res_bus.at[0, "vm_pu"],
            math.radians(network.res_bus.at[0, "va_degree"]),
        )

        # Bus IDs and reference drops are documented in calculations.ipynb.
        reference_drops = {
            2: 0.5338014092529345,
            1: 0.3271683936976548,
            5: 1.4123959816929648,
        }

        for bus, expected_drop_percent in reference_drops.items():
            load_voltage = cmath.rect(
                network.res_bus.at[bus, "vm_pu"],
                math.radians(network.res_bus.at[bus, "va_degree"]),
            )
            actual_drop_percent = abs(load_voltage - source_voltage) * 100

            with self.subTest(bus=bus):
                self.assertAlmostEqual(
                    actual_drop_percent,
                    expected_drop_percent,
                    places=3,
                )


if __name__ == "__main__":
    unittest.main()
