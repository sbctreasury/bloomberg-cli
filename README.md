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

Install the optional agent skill globally for Codex, Claude Code, Cursor, and
other compatible agents:

```powershell
npx skills add sbctreasury/bloomberg-cli --skill bloomberg-cli -g -y
```

The skill does not install or download executable code. Install the CLI first;
the skill only teaches compatible agents how to use the existing `bloomberg`
command safely.

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

## Fixed income and curves

```powershell
# Reference data, risk, spreads, cash flows, key rates, and YAS analytics
bloomberg bond info "AM383401 Corp"
bloomberg bond risk "AM383401 Corp" --settle-date 2026-07-10
bloomberg bond spreads "AM383401 Corp" --benchmark "GT10 Govt"
bloomberg bond cashflows "AM383401 Corp"
bloomberg bond key-rates "AM383401 Corp"
bloomberg bond yas "AM383401 Corp" --fields YAS_BOND_YLD YAS_OAS_SPRD

# Find an issuer's bonds and search Bloomberg curves
bloomberg bond corporate "AAPL US Equity"
bloomberg bond corporate "AAPL US Equity" --maturity-year 2027
bloomberg curve search --country US --currency USD
bloomberg curve governments Treasury
```

## Screens and custom metrics

The focused BQL commands accept raw universe, metric, grouping, and filter
expressions while handling the query structure. `aggregate` returns one row per
group rather than repeating the same aggregate on every constituent.

```powershell
bloomberg screen `
  --universe "members('SPX Index')" `
  --fields "name()" "gics_sector_name()" "px_last()" `
  --where "px_last() > 100"

bloomberg aggregate `
  --universe "members('SPX Index')" `
  --let "current=is_eps(fa_period_type=A, fa_period_offset=0)" `
  --let "prior=is_eps(fa_period_type=A, fa_period_offset=-1)" `
  --metric "(#current / #prior) - 1" `
  --group "gics_sector_name()" `
  --where "#metric > 0" `
  --stat count `
  --name positive_growth_companies
```

For longer BQL, avoid shell quoting entirely:

```powershell
bloomberg bql --file query.bql
Get-Content query.bql | bloomberg bql --file -
```

## Complete xbbg surface

The CLI discovers public functions dynamically from `xbbg`, `xbbg.ext`, and
`xbbg.markets`. This provides immediate access to new xbbg functions without a
new CLI release.

```powershell
# Discover functions and inspect signatures
bloomberg functions --search bond
bloomberg info ext.bond_info

# Call any xbbg function with JSON positional and keyword arguments
bloomberg call bdp `
  --arg "AAPL US Equity" `
  --arg PX_LAST `
  --kw backend=pandas

bloomberg call ext.bond_info `
  --arg "T 4.5 05/15/38 Govt"

bloomberg call markets.market_info `
  --arg "AAPL US Equity"
```

Qualified names such as `ext.bond_info` and `markets.market_info` identify the
xbbg namespace explicitly. Unambiguous extension functions also have short
aliases. Both synchronous and asynchronous functions are supported; async
functions are executed to completion by the CLI. Functions returning a live
`Subscription` are consumed for up to 10 batches or 10 seconds by default:

```powershell
bloomberg call subscribe `
  --arg "AAPL US Equity" `
  --arg LAST_PRICE `
  --kw tick_mode=true `
  --stream-count 5 `
  --stream-seconds 15
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
