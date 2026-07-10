"""Dynamic discovery and invocation for the public xbbg Python surface."""

from __future__ import annotations

import asyncio
import dataclasses
import enum
import inspect
from typing import Any, Callable

from .compat import suppress_dependency_syntax_warnings


def registry(*, include_aliases: bool = True) -> dict[str, Callable[..., Any]]:
    """Return public xbbg functions from core, extensions, and markets."""
    with suppress_dependency_syntax_warnings():
        import xbbg
        import xbbg.ext
        import xbbg.markets

    found: dict[str, Callable[..., Any]] = {}
    for prefix, module in (("", xbbg), ("ext.", xbbg.ext), ("markets.", xbbg.markets)):
        for name in dir(module):
            if name.startswith("_"):
                continue
            value = getattr(module, name)
            if not callable(value) or inspect.isclass(value):
                continue
            qualified = f"{prefix}{name}"
            found[qualified] = value
            # Extension/market functions also get a short name when unambiguous.
            if include_aliases and prefix and name not in found:
                found[name] = value
    return found


def describe(name: str, function: Callable[..., Any]) -> dict[str, Any]:
    try:
        signature = str(inspect.signature(function))
    except (TypeError, ValueError):
        signature = ""
    documentation = inspect.getdoc(function) or ""
    return {
        "name": name,
        "signature": signature,
        "async": inspect.iscoroutinefunction(function),
        "module": getattr(function, "__module__", ""),
        "description": documentation.splitlines()[0] if documentation else "",
    }


def catalog(search: str | None = None) -> list[dict[str, Any]]:
    needle = (search or "").lower()
    rows = [
        describe(name, function)
        for name, function in registry(include_aliases=False).items()
    ]
    if needle:
        rows = [
            row
            for row in rows
            if needle in row["name"].lower()
            or needle in row["description"].lower()
            or needle in row["module"].lower()
        ]
    return sorted(rows, key=lambda row: row["name"])


def invoke(name: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
    functions = registry()
    if name not in functions:
        raise ValueError(f"Unknown xbbg function: {name}. Use 'bloomberg functions' to discover names.")
    function = functions[name]
    result = function(*args, **kwargs)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    return result


async def _consume(subscription: Any, count: int, seconds: float) -> list[Any]:
    rows: list[Any] = []
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    try:
        while len(rows) < count:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                item = await asyncio.wait_for(subscription.__anext__(), timeout=remaining)
            except (asyncio.TimeoutError, StopAsyncIteration):
                break
            rows.append(normalize(item))
    finally:
        unsubscribe = getattr(subscription, "unsubscribe", None)
        if unsubscribe is not None:
            result = unsubscribe()
            if inspect.isawaitable(result):
                await result
    return rows


def consume_subscription(subscription: Any, count: int, seconds: float) -> Any:
    """Collect bounded output from an xbbg Subscription result."""
    if not hasattr(subscription, "__anext__"):
        return subscription
    return asyncio.run(_consume(subscription, count=count, seconds=seconds))


def normalize(value: Any) -> Any:
    """Normalize xbbg return types into dataframes or JSON-safe values."""
    module = type(value).__module__ or ""
    if module.startswith(("pandas", "polars")) and hasattr(value, "columns"):
        return value
    if hasattr(value, "to_pandas") and not module.startswith(("pandas", "polars")):
        try:
            return value.to_pandas()
        except Exception:
            pass
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return normalize(dataclasses.asdict(value))
    if isinstance(value, enum.Enum):
        return normalize(value.value)
    if isinstance(value, dict):
        return {str(key): normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [normalize(item) for item in value]
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
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "__dict__"):
        return {str(key): normalize(item) for key, item in vars(value).items() if not key.startswith("_")}
    return str(value)
