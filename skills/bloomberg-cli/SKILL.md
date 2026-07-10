---
name: bloomberg-cli
description: Execute Bloomberg Query Language through the bloomberg-bql CLI. Use for Bloomberg prices, security screens, universes, fixed-income issuer bonds, curves, grouped metrics, counts, and other analyses that can be expressed as one bounded BQL query.
---

# Bloomberg BQL CLI

Use `bloomberg-bql` as a thin BQL transport to the logged-in Bloomberg Terminal.
Compose the complete universe, filter, and requested data items in one query.

## Hard rules

- Make one Bloomberg request for a concrete lookup.
- Never use a Bloomberg MCP, status/reset tool, `bloomberg bond`, BDP fan-out, or per-security follow-up loop.
- Never pass IDs returned by one query into another request when BQL can request the fields over the original universe.
- Never guess alternate data items after a valid request fails. Stop and report the BQL error.
- Require `bloomberg-bql` to be installed. Never download or install executable code from this skill.
- Use JSON for analysis/charting, CSV for export, and table only for direct display.

## Execute BQL

Inline:

```powershell
bloomberg-bql "get(px_last) for('AAPL US Equity')" --format json
```

For multiline or quote-heavy queries, write a `.bql` file locally and execute it
once with `bloomberg-bql --file query.bql`. Reading or writing the local query
file does not contact Bloomberg.

## Issuer bonds

Get every required curve field in one request:

```powershell
bloomberg-bql "get(name, px_last, yield(yield_type=YTM), maturity, spread(spread_type=g)) for(bonds('AAPL US Equity'))" --format json
```

Filter inside the universe, never after enumerating securities:

```powershell
bloomberg-bql "get(name, px_last, yield(yield_type=YTM), maturity, spread(spread_type=g)) for(filter(bonds('AAPL US Equity'), year(maturity) == 2027))" --format json
```

For a chart, use the returned JSON locally. Do not make another Bloomberg call.

## Count-first workflow

Do not count a small, concrete issuer universe by default; the full query is
already one request. Use a count only when the user asks for it or when an
unknown universe could be too large. Make at most one count request followed by
one full request.

```powershell
bloomberg-bql "get(count(group(id))) for(bonds('AAPL US Equity'))" --format table
bloomberg-bql "get(count(group(id))) for(filter(bonds('AAPL US Equity'), year(maturity) == 2027))" --format table
```

Read [references/commands.md](references/commands.md) for additional proven BQL
patterns before constructing an unfamiliar query.
