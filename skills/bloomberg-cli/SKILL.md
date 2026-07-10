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

Before guessing a Bloomberg data item, run `bloomberg fields "plain language
description"`. Use `bloomberg info FUNCTION` before constructing an unfamiliar
generic call.

## Run reliably

Expect JSON unless a user asks for `--format csv` or `--format table`. Check the
exit code and report the structured stderr error. Do not perform a separate
session preflight, restart Bloomberg, or look for BQNT. If `bloomberg` is not on
PATH, prefix the command with:

```powershell
uvx --from git+https://github.com/sbctreasury/bloomberg-cli.git bloomberg
```

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

Read [references/commands.md](references/commands.md) when command syntax,
supported options, or additional examples are needed.
