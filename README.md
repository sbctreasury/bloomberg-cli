# Bloomberg CLI

Fast, JSON-first Bloomberg Terminal commands powered directly by
[xbbg](https://github.com/alpha-xone/xbbg). Designed for agents, automation,
and terminal users who want Bloomberg data without an MCP transport layer.

This is independent open-source software and is not affiliated with,
endorsed by, or sponsored by Bloomberg Finance L.P. Bloomberg data access
requires appropriate Bloomberg licenses and entitlements.

## Requirements

- Bloomberg Terminal running and logged in
- Windows with Bloomberg Desktop API access
- [uv](https://docs.astral.sh/uv/)

## Run from GitHub

```powershell
uvx --from git+https://github.com/sbctreasury/bloomberg-cli.git bloomberg price "AAPL US Equity"
```

## Commands

```powershell
bloomberg price "AAPL US Equity"

bloomberg bdp `
  --securities "AAPL US Equity" "MSFT US Equity" `
  --fields PX_LAST NAME

bloomberg bdh `
  --securities "AAPL US Equity" `
  --fields PX_LAST `
  --start 2025-01-01 `
  --periodicity M

bloomberg bql "get(px_last) for(['AAPL US Equity'])"

bloomberg fields "cumulative collateral loss" --limit 10
```

JSON is the default output. Data commands also support `--format csv` and
`--format table`.

## Design

- Direct xbbg calls with no status preflight or session reset
- Lazy imports for fast help and argument parsing
- Structured JSON errors on stderr and non-zero exit codes
- No MCP, charting, browser, hook, or BQNT dependencies

## Development

```powershell
uv sync --extra dev
uv run pytest
uv build
```
