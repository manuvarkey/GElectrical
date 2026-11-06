"""Regression test for weighted generator slack participation."""

import unittest

import pandapower as pp


class GeneratorDistributedSlackTest(unittest.TestCase):
    def test_generator_slack_weight_controls_balancing_share(self):
        network = pp.create_empty_network()
        source_bus = pp.create_bus(network, vn_kv=20.0)
        generator_bus = pp.create_bus(network, vn_kv=20.0)
        pp.create_ext_grid(network, bus=source_bus, vm_pu=1.0)
        pp.create_line_from_parameters(
            network,
            from_bus=source_bus,
            to_bus=generator_bus,
            length_km=1.0,
            r_ohm_per_km=0.1,
            x_ohm_per_km=0.1,
            c_nf_per_km=0.0,
            max_i_ka=1.0,
        )
        generator_index = pp.create_gen(
            network,
            bus=generator_bus,
            p_mw=0.2,
            vm_pu=1.0,
            slack=True,
            slack_weight=3.0,
        )
        pp.create_load(network, bus=generator_bus, p_mw=1.0, q_mvar=0.2)

        pp.runpp(network, calculate_voltage_angles=True, distributed_slack=True)

        generator_share = (
            network.res_gen.at[generator_index, "p_mw"]
            - network.gen.at[generator_index, "p_mw"]
        )
        external_grid_share = network.res_ext_grid["p_mw"].sum()

        self.assertGreater(generator_share, 0.0)
        self.assertGreater(external_grid_share, 0.0)
        self.assertAlmostEqual(generator_share / external_grid_share, 3.0, places=3)


if __name__ == "__main__":
    unittest.main()
