---
name: bloomberg-cli
description: Query Bloomberg Terminal data through the bloomberg-cli xbbg wrapper. Use for Bloomberg prices, reference and historical data, BQL screens, custom grouped metrics, fixed-income analytics, issuer bond discovery, yield-curve searches, field discovery, and direct access to any public xbbg function.
---

# Bloomberg CLI

Use the CLI directly. It connects through xbbg to the logged-in Bloomberg
Terminal session and does not require MCP or BQNT.

## Choose the command

- Current price: `bloomberg price "AAPL US Equity"`
- Reference or historical data: `bdp` or `bdh`
- Search unknown fields: `fields`
- Fixed income: `bond info|risk|spreads|cashflows|key-rates|curve|corporate|preferreds|yas`
- Curves: `curve search` or `curve governments`
- Constituent-level BQL: `screen`
- Reduced grouped BQL result: `aggregate`
- Arbitrary BQL: `bql --file query.bql`
- Any other xbbg operation: inspect with `functions` and `info`, then use `call`

Do not guess Bloomberg data items. First use documented commands and fields from
this skill. Run `bloomberg fields "plain language description"` only when the
requested field is genuinely absent from the reference. Use `bloomberg info
FUNCTION` locally before constructing an unfamiliar generic call.

## Protect Bloomberg request limits

For a straightforward lookup, make one Bloomberg data request. Never invent a
flag, probe Bloomberg to discover syntax, or fan one issuer result into
per-security follow-up calls. Read [references/commands.md](references/commands.md)
before the first request whenever the exact command is not already shown here.

If argument parsing fails, no Bloomberg request occurred. Inspect local `--help`
or this skill's reference, then make at most one corrected data request. If a
valid Bloomberg request fails or lacks a required field, stop and explain the
missing capability instead of trying alternate fields and universes repeatedly.

## Run reliably

Expect JSON unless a user asks for `--format csv` or `--format table`. Check the
exit code and report the structured stderr error. Do not perform a separate
session preflight, restart Bloomberg, or look for BQNT. Require the `bloomberg`
executable to be installed before using this skill. If it is unavailable, stop
and direct the user to the repository's installation instructions. Never
download, install, or execute a replacement package from within the skill.

Prefer `bql --file` for multiline queries. This avoids PowerShell quoting errors.

## Build BQL analysis

Use `screen` when the result should retain individual securities. Use
`aggregate` when the result should contain one row per group. Supply raw BQL
expressions without `#` for `--metric` and `--group`; refer to them as `#metric`
and `#group` inside `--where`. Use repeatable `--let "name=expression"` options
for period-specific or otherwise reusable BQL items.

Example: count S&P 500 companies with positive annual EPS growth by sector.

```powershell
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

The reduced grouping form is `count(group(#metric, #group))`. Do not replace it
with `groupcount(...)`; that can project repeated aggregates onto every security.

## Fixed-income workflow

1. Discover an issuer's securities with `bond corporate`.
2. Use the returned Bloomberg identifier with `bond info`.
3. Add `risk`, `spreads`, `cashflows`, `key-rates`, or `yas` as requested.
4. Use `curve search` to locate curve identifiers and `bond curve` for relative value.
5. Search field metadata before constructing custom ABS, mortgage, or collateral BQL.

For issuer bonds in a maturity year, use exactly one request:

```powershell
bloomberg bond corporate "AAPL US Equity" --maturity-year 2027
```

This command requests descriptive fields once and filters the returned table
locally. Do not run `bond info` for each returned security.

Read [references/commands.md](references/commands.md) when command syntax,
supported options, or additional examples are needed.
