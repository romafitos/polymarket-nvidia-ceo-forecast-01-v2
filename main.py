"""Quantile forecaster for Polymarket's Next CEO of NVIDIA? prices.

For each market in a case this program forecasts the Yes price at every
minute 1..240 ahead, as five quantiles (0.05, 0.25, 0.5, 0.75, 0.95).
The centre of the forecast is the last price seen, and the forecast
widens with horizon according to how jumpy that market has been lately.

How the width is set: for each market take the root-mean-square of its
one-minute price changes over the last 120 minutes, floored at 0.0005
and capped at 0.02. Spreads grow as h**0.33, slower than a random walk,
because measured 240-minute moves are far smaller than sqrt(h) would
predict. The five quantile offsets are scaled normal quantiles: the
lower tail is stretched by 1.5, the upper tail by 1.3, the lower
shoulder is kept at 0.7 and the upper shoulder is tightened to 0.5,
which matches the measured coverage on backtest cuts (the upper
shoulder of the raw normal is too wide, the lower tail too narrow).

The 24 outcomes are mutually exclusive, so their Yes prices should
add up to about 1. When the sum sits above 1, every centre is pulled
down toward the sum-to-one constraint, but gradually: the pull grows
with horizon as (1 - exp(-h/60)), so the first minutes barely move
and the full correction lands by about four hours. The pull strength
is 0.35 of the excess share.

Standard library only, deterministic, no network, no clock, no random
numbers. Reads every *.in file in $MAKEFUN_INPUT_DIR (else /input)
and writes one <id>.out per case to $MAKEFUN_OUTPUT_DIR (else
/output).
"""

import json
import math
import os
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
# Scaled normal quantile offsets: lower tail x1.5, lower shoulder x0.7,
# median 0, upper shoulder x0.5, upper tail x1.3. These multipliers
# were fitted on 15 local backtest cuts (6 kit practice cases plus 9
# live checkpoints); the tight upper shoulder is the single biggest
# win over a plain normal, worth about a third of the total gain.
Z = [-2.467281, -0.472143, 0.0, 0.337245, 2.138310]

VOL_WINDOW = 120          # minutes of recent history used for sigma
VOL_FLOOR = 0.0005        # minimum per-minute sigma
VOL_CAP = 0.02            # maximum per-minute sigma
GROWTH = 0.33             # spread grows as h ** GROWTH
SUM_PULL = 0.35           # fraction of the sum-to-one correction applied
PULL_TAU = 60.0           # minutes over which the sum pull phases in


def clean(value):
    """Clamp to [0, 1], round to 6 decimals, and never return -0.0."""
    return round(min(1.0, max(0.0, value)), 6) + 0.0


def recent_sigma(prices):
    """RMS of one-minute price differences over the last 120 minutes."""
    if len(prices) < 2:
        return VOL_FLOOR
    # 120 one-minute differences need the last 121 prices; fewer
    # prices means use everything available.
    tail = prices[-121:] if len(prices) > 121 else prices
    total = 0.0
    count = 0
    for prev, cur in zip(tail, tail[1:]):
        diff = cur - prev
        total += diff * diff
        count += 1
    if count == 0:
        return VOL_FLOOR
    sigma = math.sqrt(total / count)
    return min(VOL_CAP, max(VOL_FLOOR, sigma))


def forecast_market(last_price, sigma, pull, horizon):
    """240 rows of five quantiles around `last_price` for one market."""
    rows = []
    for h in range(1, horizon + 1):
        # The sum-to-one pull phases in over PULL_TAU minutes.
        centre = last_price * (1.0 - pull * (1.0 - math.exp(-h / PULL_TAU)))
        spread = sigma * (h ** GROWTH)
        rows.append([clean(centre + z * spread) for z in Z])
    return rows


def forecast_case(case):
    if case["quantiles"] != QUANTILES:
        raise ValueError(
            "quantiles %r do not match expected %r"
            % (case["quantiles"], QUANTILES)
        )
    horizon = case["horizon_minutes"]
    markets = case["markets"]

    last_prices = [m["prices"][-1] for m in markets]
    total = sum(last_prices)
    # The 24 outcomes are mutually exclusive, so their Yes prices
    # should sum to about 1; pull each centre part of the way toward
    # that constraint, phased in over the horizon (see PULL_TAU).
    pull = SUM_PULL * (total - 1.0) / total if total > 0 else 0.0

    forecasts = []
    for market in markets:
        if not market["prices"]:
            raise ValueError("market %s has no prices" % market["id"])
        sigma = recent_sigma(market["prices"])
        forecasts.append(
            {
                "id": market["id"],
                "q": forecast_market(
                    market["prices"][-1], sigma, pull, horizon
                ),
            }
        )
    return {"forecasts": forecasts}


def main():
    in_dir = Path(INPUT_DIR)
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in sorted(p.name for p in in_dir.glob("*.in")):
        case = json.loads((in_dir / name).read_text(encoding="utf-8"))
        result = forecast_case(case)
        out_path = out_dir / (name[:-3] + ".out")
        out_path.write_text(
            json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
