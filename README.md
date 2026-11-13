# Polymarket NVIDIA CEO forecast — v2

Forecasts Polymarket's "Next CEO of NVIDIA?" Yes prices minute by
minute, 4 hours ahead, as five quantiles (0.05, 0.25, 0.5, 0.75, 0.95)
for each of the 24 candidate markets.

## Method

- **Centre:** the last price seen. Prices are martingales at this
  horizon — every drift variant tested made the score worse.
- **Width:** per-market RMS of one-minute price changes over the last
  120 minutes (floor 0.0005, cap 0.02), growing as h**0.33 — much
  slower than a random walk, matching measured 240-minute moves.
- **Quantile shape:** scaled normal offsets — lower tail ×1.5, lower
  shoulder ×0.7, upper shoulder ×0.5, upper tail ×1.3. The tight upper
  shoulder is the biggest single win over v1.
- **Sum-to-one pull:** the 24 outcomes are mutually exclusive, so
  their Yes prices should sum to ~1. When the sum sits above 1, every
  centre is pulled down 0.35 of the excess share, phased in over 60
  minutes — the first minutes barely move, the full correction lands
  by four hours.

## Local validation (15 backtest cuts)

Mean pinball loss, lower is better. House persistence baseline: 0.3686.

| config | 12-cut | practice (kit, item-weighted) | 3 fresh holdout cuts |
|---|---|---|---|
| v1 (submitted) | 0.266443 | 0.266104 | 0.109770 |
| **v2** | **0.263464** | **0.263558** | **0.108946** |

v2 beats v1 on all three cut families and on 8 of the 12 cuts
individually. The 3 fresh holdout cuts are checkpoints from the
morning of 13 Nov 2026 (05:00/06:00/07:00 UTC), built from live
Polymarket history fetched after v1 was submitted, so they were never
used to pick any parameter. Practice score 0.2636 sits below the live
top-100 cutoff (~0.265) at the time of submission.

## Run

```sh
python3 main.py   # reads $MAKEFUN_INPUT_DIR (default /input), writes $MAKEFUN_OUTPUT_DIR (default /output)
```

Standard library only, deterministic, no network, no clock, no
random numbers. One `*.out` file per `*.in` case, 240 rows × 5
quantiles per market.

## Referral

Referral code: qeky27wz
