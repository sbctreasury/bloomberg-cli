import json

import pandas as pd

from bloomberg_cli import cli
from bloomberg_cli import surface
from bloomberg_cli.workflows import build_aggregate, build_screen


def test_frame_records_converts_dataframe():
    frame = pd.DataFrame([{"ticker": "AAPL US Equity", "field": "PX_LAST", "value": 123.45}])
    assert cli.frame_records(frame) == [
        {"ticker": "AAPL US Equity", "field": "PX_LAST", "value": 123.45}
    ]


def test_price_json(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "price",
        lambda security, field: {
            "security": security,
            "field": field,
            "value": 123.45,
            "elapsed_ms": 1.0,
        },
    )
    assert cli.run(["price", "AAPL US Equity"]) == 0
    assert json.loads(capsys.readouterr().out)["value"] == 123.45


def test_errors_are_structured(monkeypatch, capsys):
    def fail(*_args):
        raise RuntimeError("not connected")

    monkeypatch.setattr(cli, "price", fail)
    assert cli.run(["price", "AAPL US Equity"]) == 1
    error = json.loads(capsys.readouterr().err)
    assert error == {
        "error": "not connected",
        "type": "RuntimeError",
        "command": "price",
    }


def test_generic_call(monkeypatch, capsys):
    monkeypatch.setattr(cli, "invoke", lambda name, args, kwargs: {"name": name, "args": args, "kwargs": kwargs})
    assert cli.run(["call", "bdp", "--args", '["AAPL US Equity", "PX_LAST"]']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["name"] == "bdp"
    assert result["args"] == ["AAPL US Equity", "PX_LAST"]


def test_generic_call_repeatable_arguments(monkeypatch, capsys):
    monkeypatch.setattr(cli, "invoke", lambda name, args, kwargs: {"name": name, "args": args, "kwargs": kwargs})
    assert cli.run([
        "call", "bdp", "--arg", "AAPL US Equity", "--arg", "PX_LAST", "--kw", "backend=pandas"
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["args"] == ["AAPL US Equity", "PX_LAST"]
    assert result["kwargs"] == {"backend": "pandas"}


def test_catalog_includes_core_and_extensions():
    names = {row["name"] for row in surface.catalog()}
    assert "bdp" in names
    assert "ext.bond_info" in names
    assert "markets.market_info" in names


def test_build_screen():
    assert build_screen("members('SPX Index')", ["name()", "px_last()"], "px_last() > 100") == (
        "get(name(), px_last()) for(filter(members('SPX Index'), px_last() > 100))"
    )


def test_build_aggregate_uses_reduced_group_shape():
    query = build_aggregate(
        "members('SPX Index')",
        "is_eps(fa_period_type=A, fa_period_offset=0)",
        "gics_sector_name()",
        "count",
        "#metric > 0",
        "positive_companies",
    )
    assert "count(group(#metric, #group))" in query
    assert "groupcount" not in query


def test_build_aggregate_supports_named_bindings():
    query = build_aggregate(
        "members('SPX Index')",
        "(#current / #prior) - 1",
        "gics_sector_name()",
        "count",
        "#metric > 0",
        bindings=[
            ("current", "is_eps(fa_period_type=A, fa_period_offset=0)"),
            ("prior", "is_eps(fa_period_type=A, fa_period_offset=-1)"),
        ],
    )
    assert "#current = is_eps" in query
    assert "#prior = is_eps" in query
    assert "#metric = (#current / #prior) - 1" in query
