import json

import pandas as pd

from bloomberg_cli import cli


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
