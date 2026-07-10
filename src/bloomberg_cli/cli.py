"""JSON-first Bloomberg Terminal commands powered directly by xbbg."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any, Sequence

from .compat import suppress_dependency_syntax_warnings
from .surface import catalog, consume_subscription, invoke, normalize, registry
from .workflows import AGGREGATES, build_aggregate, build_screen


CORPORATE_BOND_FIELDS = ["NAME", "SECURITY_DES", "MATURITY", "CPN", "AMT_OUTSTANDING"]


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            pass
    return value


def frame_records(frame: Any) -> list[dict[str, Any]]:
    """Convert an xbbg dataframe result into JSON-safe records."""
    if frame is None or frame.empty:
        return []
    return [
        {str(key): _json_value(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def emit(frame: Any, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(frame_records(frame), default=str))
    elif output_format == "csv":
        print(frame.to_csv(index=False), end="")
    else:
        print(frame.to_string(index=False))


def emit_value(value: Any, output_format: str) -> None:
    """Emit either a dataframe-like or scalar/structured result."""
    value = normalize(value)
    if hasattr(value, "to_dict") and hasattr(value, "columns"):
        emit(value, output_format)
        return
    if output_format == "json":
        print(json.dumps(value, default=str))
    else:
        print(value)


def filter_maturity_year(frame: Any, year: int) -> Any:
    """Filter an issuer-bond result locally without another Bloomberg request."""
    frame = normalize(frame)
    maturity_column = next((column for column in frame.columns if str(column).upper() == "MATURITY"), None)
    if maturity_column is None:
        raise RuntimeError("Bloomberg issuer-bond result did not contain MATURITY")
    return frame[frame[maturity_column].astype(str).str.startswith(f"{year:04d}-")]


def _blp():
    # Deliberately lazy: help and argument errors do not import pandas/xbbg.
    with suppress_dependency_syntax_warnings():
        from xbbg import blp

    return blp


def parse_token(value: str) -> Any:
    """Parse JSON scalars/containers, falling back to the original string."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def parse_keywords(values: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Keyword argument must use key=value: {value}")
        key, raw = value.split("=", 1)
        result[key] = parse_token(raw)
    return result


def parse_bindings(values: list[str]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for value in values:
        if "=" not in value:
            raise ValueError(f"BQL binding must use name=expression: {value}")
        name, expression = value.split("=", 1)
        result.append((name.strip().removeprefix("#"), expression.strip()))
    return result


def price(security: str, field: str) -> dict[str, Any]:
    started = time.perf_counter()
    frame = _blp().bdp(security, field, backend="pandas")
    records = frame_records(frame)
    if not records:
        raise RuntimeError(f"Bloomberg returned no {field} value for {security}")
    row = records[0]
    result = {
        "security": str(row.get("ticker", security)),
        "field": str(row.get("field", field)),
        "value": row.get("value", next(iter(row.values()))),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
    }
    return result


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="bloomberg",
        description="Direct Bloomberg Terminal commands powered by xbbg.",
    )
    root.add_argument("--version", action="version", version="%(prog)s 0.2.0")
    commands = root.add_subparsers(dest="command", required=True)

    price_cmd = commands.add_parser("price", help="Get a current security price")
    price_cmd.add_argument("security")
    price_cmd.add_argument("--field", default="PX_LAST")
    price_cmd.add_argument("--format", choices=("json", "table"), default="json")

    bdp = commands.add_parser("bdp", help="Get Bloomberg reference data")
    bdp.add_argument("--securities", nargs="+", required=True)
    bdp.add_argument("--fields", nargs="+", required=True)
    bdp.add_argument("--format", choices=("json", "csv", "table"), default="json")

    bdh = commands.add_parser("bdh", help="Get Bloomberg historical data")
    bdh.add_argument("--securities", nargs="+", required=True)
    bdh.add_argument("--fields", nargs="+", required=True)
    bdh.add_argument("--start", required=True)
    bdh.add_argument("--end", default="today")
    bdh.add_argument("--periodicity", choices=("D", "W", "M", "Q", "Y"), default="D")
    bdh.add_argument("--format", choices=("json", "csv", "table"), default="json")

    bql = commands.add_parser("bql", help="Execute a raw BQL query")
    bql.add_argument("query", nargs="?")
    bql.add_argument("--file", help="Read BQL from a file; use - for stdin")
    bql.add_argument("--format", choices=("json", "csv", "table"), default="json")

    fields = commands.add_parser("fields", help="Search Bloomberg field metadata")
    fields.add_argument("query")
    fields.add_argument("--limit", type=int, default=20)
    fields.add_argument("--format", choices=("json", "csv", "table"), default="json")

    bond = commands.add_parser("bond", help="Fixed-income reference, risk, spread, and cash-flow analytics")
    bond.add_argument("analytic", choices=("info", "risk", "spreads", "cashflows", "key-rates", "curve", "corporate", "preferreds", "yas"))
    bond.add_argument("securities", nargs="+")
    bond.add_argument("--fields", nargs="+")
    bond.add_argument("--settle-date")
    bond.add_argument("--benchmark")
    bond.add_argument("--maturity-year", type=int, help="Filter issuer bonds locally by maturity year")
    bond.add_argument("--format", choices=("json", "csv", "table"), default="json")

    curve = commands.add_parser("curve", help="Search Bloomberg curves and government securities")
    curve.add_argument("kind", choices=("search", "governments"), default="search")
    curve.add_argument("query", nargs="?")
    curve.add_argument("--country")
    curve.add_argument("--currency")
    curve.add_argument("--curve-type")
    curve.add_argument("--subtype")
    curve.add_argument("--curve-id")
    curve.add_argument("--format", choices=("json", "csv", "table"), default="json")

    screen = commands.add_parser("screen", help="Run a BQL universe screen")
    screen.add_argument("--universe", required=True, help="Raw BQL universe expression")
    screen.add_argument("--fields", nargs="+", required=True)
    screen.add_argument("--where", help="Raw BQL filter expression")
    screen.add_argument("--show-query", action="store_true")
    screen.add_argument("--format", choices=("json", "csv", "table"), default="json")

    aggregate = commands.add_parser("aggregate", help="Group and aggregate a custom BQL metric")
    aggregate.add_argument("--universe", required=True)
    aggregate.add_argument("--metric", required=True)
    aggregate.add_argument("--group", required=True)
    aggregate.add_argument("--let", action="append", default=[], metavar="NAME=EXPR", help="Reusable BQL definition; repeat as needed")
    aggregate.add_argument("--stat", choices=sorted(AGGREGATES), required=True)
    aggregate.add_argument("--where", help="Filter expression; #metric and #group are available")
    aggregate.add_argument("--name", default="value")
    aggregate.add_argument("--show-query", action="store_true")
    aggregate.add_argument("--format", choices=("json", "csv", "table"), default="json")

    functions = commands.add_parser("functions", help="List every callable in the xbbg public surface")
    functions.add_argument("--search", help="Filter by function, module, or description")
    functions.add_argument("--format", choices=("json", "table"), default="table")

    info = commands.add_parser("info", help="Show the signature and documentation summary for an xbbg function")
    info.add_argument("function")

    call = commands.add_parser("call", help="Call any public xbbg function using JSON arguments")
    call.add_argument("function")
    call.add_argument("--args", default="[]", help="JSON positional argument array")
    call.add_argument("--kwargs", default="{}", help="JSON keyword argument object")
    call.add_argument("--arg", action="append", default=[], help="Repeatable positional argument; JSON values are decoded")
    call.add_argument("--kw", action="append", default=[], help="Repeatable key=value argument; JSON values are decoded")
    call.add_argument("--stream-count", type=int, default=10, help="Maximum batches for subscription results")
    call.add_argument("--stream-seconds", type=float, default=10.0, help="Maximum seconds for subscription results")
    call.add_argument("--format", choices=("json", "csv", "table"), default="json")
    return root


def run(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "price":
            result = price(args.security, args.field.upper())
            if args.format == "json":
                print(json.dumps(result, default=str))
            else:
                print(f"{result['security']}  {result['field']}  {result['value']}")
            return 0

        if args.command == "functions":
            rows = catalog(args.search)
            if args.format == "json":
                print(json.dumps(rows))
            else:
                import pandas as pd

                print(pd.DataFrame(rows).to_string(index=False))
            return 0

        if args.command == "info":
            functions = registry()
            if args.function not in functions:
                raise ValueError(f"Unknown xbbg function: {args.function}")
            row = next(item for item in catalog() if item["name"] == args.function)
            print(json.dumps(row))
            return 0

        if args.command == "call":
            positional = json.loads(args.args)
            keywords = json.loads(args.kwargs)
            if not isinstance(positional, list):
                raise ValueError("--args must be a JSON array")
            if not isinstance(keywords, dict):
                raise ValueError("--kwargs must be a JSON object")
            positional.extend(parse_token(value) for value in args.arg)
            keywords.update(parse_keywords(args.kw))
            result = invoke(args.function, positional, keywords)
            result = consume_subscription(result, args.stream_count, args.stream_seconds)
            emit_value(result, args.format)
            return 0

        if args.command == "bond":
            mapping = {
                "info": "ext.bond_info",
                "risk": "ext.bond_risk",
                "spreads": "ext.bond_spreads",
                "cashflows": "ext.bond_cashflows",
                "key-rates": "ext.bond_key_rates",
                "curve": "ext.bond_curve",
                "corporate": "ext.corporate_bonds",
                "preferreds": "ext.preferreds",
                "yas": "ext.yas",
            }
            positional: list[Any] = [args.securities if args.analytic in {"curve", "yas"} else args.securities[0]]
            keywords: dict[str, Any] = {}
            requested_fields = args.fields
            if args.maturity_year:
                if args.analytic != "corporate":
                    raise ValueError("--maturity-year is only supported by bond corporate")
                requested_fields = list(requested_fields or CORPORATE_BOND_FIELDS)
                if not any(field.upper() == "MATURITY" for field in requested_fields):
                    requested_fields.append("MATURITY")
            if requested_fields:
                if args.analytic in {"curve", "yas"}:
                    keywords["flds"] = requested_fields
                elif args.analytic in {"corporate", "preferreds"}:
                    keywords["fields"] = requested_fields
                else:
                    raise ValueError(f"--fields is not supported by bond {args.analytic}")
            if args.settle_date:
                if args.analytic not in {"risk", "spreads", "cashflows", "key-rates", "curve", "yas"}:
                    raise ValueError(f"--settle-date is not supported by bond {args.analytic}")
                keywords["settle_dt"] = args.settle_date
            if args.benchmark:
                if args.analytic not in {"spreads", "yas"}:
                    raise ValueError(f"--benchmark is not supported by bond {args.analytic}")
                keywords["benchmark"] = args.benchmark
            result = invoke(mapping[args.analytic], positional, keywords)
            if args.maturity_year:
                result = filter_maturity_year(result, args.maturity_year)
            emit_value(result, args.format)
            return 0

        blp = _blp()
        if args.command == "bdp":
            frame = blp.bdp(args.securities, args.fields, backend="pandas")
        elif args.command == "bdh":
            frame = blp.bdh(
                args.securities,
                args.fields,
                start_date=args.start,
                end_date=args.end,
                Per=args.periodicity,
                backend="pandas",
            )
        elif args.command == "bql":
            if args.file:
                query = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
            elif args.query:
                query = args.query
            elif not sys.stdin.isatty():
                query = sys.stdin.read()
            else:
                raise ValueError("Provide a BQL query, --file PATH, or stdin")
            frame = blp.bql(query, backend="pandas")
        elif args.command == "fields":
            search = getattr(blp, "bfld", None) or blp.fieldSearch
            frame = search(search_spec=args.query, backend="pandas").head(args.limit)
        elif args.command == "curve":
            if args.kind == "governments":
                frame = blp.bgovts(args.query, backend="pandas")
            else:
                frame = blp.bcurves(
                    country=args.country,
                    currency=args.currency,
                    curve_type=args.curve_type,
                    subtype=args.subtype,
                    curveid=args.curve_id,
                    backend="pandas",
                )
        elif args.command == "screen":
            query = build_screen(args.universe, args.fields, args.where)
            if args.show_query:
                print(query, file=sys.stderr)
            frame = blp.bql(query, backend="pandas")
        elif args.command == "aggregate":
            query = build_aggregate(
                args.universe,
                args.metric,
                args.group,
                args.stat,
                args.where,
                args.name,
                parse_bindings(args.let),
            )
            if args.show_query:
                print(query, file=sys.stderr)
            frame = blp.bql(query, backend="pandas")
        else:  # pragma: no cover
            raise RuntimeError(f"Unsupported command: {args.command}")
        emit(frame, args.format)
        return 0
    except Exception as exc:
        error = {"error": str(exc), "type": type(exc).__name__, "command": args.command}
        print(json.dumps(error), file=sys.stderr)
        return 1


def main() -> None:
    raise SystemExit(run())
