"""First-class BQL builders for screening and custom aggregation."""

from __future__ import annotations

import re


AGGREGATES = {"count", "avg", "sum", "min", "max", "median", "std"}


def build_screen(universe: str, fields: list[str], where: str | None = None) -> str:
    population = f"filter({universe}, {where})" if where else universe
    return f"get({', '.join(fields)}) for({population})"


def build_aggregate(
    universe: str,
    metric: str,
    group: str,
    statistic: str,
    where: str | None = None,
    name: str = "value",
    bindings: list[tuple[str, str]] | None = None,
) -> str:
    if statistic not in AGGREGATES:
        raise ValueError(f"Unsupported statistic: {statistic}")
    definitions: list[str] = []
    for binding_name, expression in bindings or []:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", binding_name):
            raise ValueError(f"Invalid BQL binding name: {binding_name}")
        definitions.append(f"  #{binding_name} = {expression};")
    definitions.extend((f"  #metric = {metric};", f"  #group = {group};"))
    population = f"filter({universe}, {where})" if where else universe
    return (
        "let(\n"
        + "\n".join(definitions)
        + "\n"
        ")\n"
        f"get({statistic}(group(#metric, #group)) as #{name})\n"
        f"for({population})"
    )
