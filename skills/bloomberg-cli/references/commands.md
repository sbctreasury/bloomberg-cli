# Bloomberg BQL patterns

## Command input and output

```powershell
bloomberg-bql "get(px_last) for('AAPL US Equity')"
bloomberg-bql "get(px_last) for('AAPL US Equity')" --format table
bloomberg-bql "get(px_last) for('AAPL US Equity')" --format csv
bloomberg-bql --file query.bql --format json
Get-Content query.bql | bloomberg-bql --file - --format json
```

## Issuer bonds

```bql
get(count(group(id))) for(bonds('AAPL US Equity'))

get(name, px_last, yield(yield_type=YTM), maturity, spread(spread_type=g))
for(bonds('AAPL US Equity'))

get(count(group(id)))
for(filter(bonds('AAPL US Equity'), year(maturity) == 2027))

get(name, px_last, yield(yield_type=YTM), maturity, spread(spread_type=g))
for(filter(bonds('AAPL US Equity'), year(maturity) == 2027))
```

## Equity aggregation

```bql
let(
  #current = is_eps(fa_period_type=A, fa_period_offset=0);
  #prior = is_eps(fa_period_type=A, fa_period_offset=-1);
  #growth = (#current / #prior) - 1;
  #sector = gics_sector_name();
)
get(count(group(#growth, #sector)) as #positive_growth_companies)
for(filter(members('SPX Index'), #growth > 0))
```

Use aggregate-over-group, such as `count(group(...))`, for one row per group.
Do not use `groupcount(...)` when a reduced result is required.
