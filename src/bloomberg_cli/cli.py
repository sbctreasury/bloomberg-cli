"""JSON-first Bloomberg Terminal commands powered directly by xbbg."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any, Sequence

from .surface import catalog, consume_subscription, invoke, normalize, registry


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


def _blp():
    # Deliberately lazy: help and argument errors do not import pandas/xbbg.
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
    root.add_argument("--version", action="version", version="%(prog)s 0.1.0")
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
    bql.add_argument("query")
    bql.add_argument("--format", choices=("json", "csv", "table"), default="json")

    fields = commands.add_parser("fields", help="Search Bloomberg field metadata")
    fields.add_argument("query")
    fields.add_argument("--limit", type=int, default=20)
    fields.add_argument("--format", choices=("json", "csv", "table"), default="json")

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
            frame = blp.bql(args.query, backend="pandas")
        elif args.command == "fields":
            search = getattr(blp, "bfld", None) or blp.fieldSearch
            frame = search(search_spec=args.query, backend="pandas").head(args.limit)
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
