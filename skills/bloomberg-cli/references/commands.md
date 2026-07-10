# Command reference

## Direct data

```powershell
bloomberg price "AAPL US Equity" --field PX_LAST
bloomberg bdp --securities "AAPL US Equity" --fields PX_LAST NAME
bloomberg bdh --securities "AAPL US Equity" --fields PX_LAST --start 2025-01-01 --periodicity M
bloomberg fields "option adjusted spread" --limit 20
```

## Fixed income

```powershell
bloomberg bond corporate "AAPL US Equity"
bloomberg bond corporate "AAPL US Equity" --maturity-year 2027
bloomberg bond info "AM383401 Corp"
bloomberg bond risk "AM383401 Corp" --settle-date 2026-07-10
bloomberg bond spreads "AM383401 Corp" --benchmark "GT10 Govt"
bloomberg bond cashflows "AM383401 Corp"
bloomberg bond key-rates "AM383401 Corp"
bloomberg bond yas "AM383401 Corp" --fields YAS_BOND_YLD YAS_OAS_SPRD
bloomberg bond curve "AM383401 Corp" "AM383402 Corp"
```

Only `curve`, `corporate`, `preferreds`, and `yas` accept `--fields`.
Only `bond corporate` accepts `--maturity-year`; it filters locally after one
issuer-bond request and supplies useful descriptive fields by default.
Only `risk`, `spreads`, `cashflows`, `key-rates`, `curve`, and `yas` accept
`--settle-date`. Only `spreads` and `yas` accept `--benchmark`.

## Curves

```powershell
bloomberg curve search --country US --currency USD
bloomberg curve search --curve-type Government --curve-id 1
bloomberg curve governments Treasury
```

## Generic xbbg surface

```powershell
bloomberg functions --search bond
bloomberg info ext.bond_info
bloomberg call bdp --arg "AAPL US Equity" --arg PX_LAST --kw backend=pandas
```

Use repeatable `--arg` and `--kw key=value` options on Windows. Values that are
valid JSON are decoded automatically.
