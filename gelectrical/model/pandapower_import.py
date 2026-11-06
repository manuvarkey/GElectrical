"""Helpers for inspecting imported Pandapower networks."""


NETWORK_TABLES = (
    ("bus", "Buses"),
    ("line", "Lines"),
    ("trafo", "Transformers"),
    ("trafo3w", "Three-winding transformers"),
    ("load", "Loads"),
    ("sgen", "Static generators"),
    ("gen", "Generators"),
    ("ext_grid", "External grids"),
    ("switch", "Switches"),
    ("shunt", "Shunts"),
    ("impedance", "Impedances"),
    ("storage", "Storage units"),
)


def load_pandapower_json(filename, pandapower_module=None):
    """Load a Pandapower JSON file without coupling callers to the package import."""
    if pandapower_module is None:
        import pandapower as pandapower_module
    return pandapower_module.from_json(filename)


def summarize_network(network):
    """Return a compact element-count summary for a Pandapower network."""
    lines = []
    for table_name, label in NETWORK_TABLES:
        table = network.get(table_name)
        count = len(table) if table is not None else 0
        if count:
            lines.append("{}: {}".format(label, count))
    if not lines:
        return "The imported network contains no recognized elements."
    return "\n".join(lines)


def _has_active_row(table, required_flag=None):
    """Return whether a table contains an in-service row matching a flag."""
    if table is None or len(table) == 0:
        return False
    for _, row in table.iterrows():
        in_service = row.get("in_service", True)
        if in_service is False:
            continue
        if str(in_service).strip().lower() in ("false", "0"):
            continue
        if required_flag is not None:
            flag = row.get(required_flag, False)
            if flag is not True and str(flag).strip().lower() not in ("true", "1"):
                continue
        return True
    return False


def validate_powerflow_slack(network):
    """Raise a useful error if no active slack source exists in the network."""
    if _has_active_row(network.get("ext_grid")):
        return
    if _has_active_row(network.get("gen"), required_flag="slack"):
        return
    raise ValueError(
        "Power flow cannot run: the imported network has no in-service "
        "external grid or slack generator. Add an ext_grid or enable a "
        "generator's slack option in the source network, then export JSON again."
    )


def run_imported_powerflow(network, pandapower_module=None):
    """Run a balanced Pandapower power flow on an imported network in place."""
    validate_powerflow_slack(network)
    if pandapower_module is None:
        import pandapower as pandapower_module
    pandapower_module.runpp(
        network,
        run_control=True,
        calculate_voltage_angles=True,
    )
    return network
