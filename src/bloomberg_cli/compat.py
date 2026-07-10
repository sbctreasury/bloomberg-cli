"""Narrow compatibility helpers for third-party Bloomberg dependencies."""

from __future__ import annotations

from contextlib import contextmanager
import warnings
from collections.abc import Iterator


@contextmanager
def suppress_dependency_syntax_warnings() -> Iterator[None]:
    """Hide Python 3.13 compile warnings emitted while importing blpapi/xbbg."""
    with warnings.catch_warnings():
        # blpapi 3.24 contains docstrings such as ``Message\s``. Python 3.13
        # reports these only when the module is first compiled, which can make
        # an otherwise successful first CLI call look like a failure.
        warnings.simplefilter("ignore", SyntaxWarning)
        yield
