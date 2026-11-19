# GTA VI Trophy Rarity Forecaster

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/ipaludhi/gta6-trophy-rarity-forecast/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/ipaludhi/gta6-trophy-rarity-forecast/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

Forecasts, for every Grand Theft Auto VI PlayStation 5 trophy, its earn rate on Exophase at 2026-11-26 00:00 UTC — a week after launch — as five quantiles (5/25/50/75/95%), from the house's recording of the trophy page up to the case checkpoint. Scored by mean pinball loss on the logit scale.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

`main.py` (Python 3.13, standard library only, no network) reads every `*.in` case in the input directory and writes one `*.out` forecast per case. Deterministic: no randomness, no wall clock.

## Model

Earners-over-players decomposition, `rate = E / N`, because a trophy's rate moves for two different reasons: new players joining dilute it (N jumps at an Exophase refresh, E barely moves) while players progressing raise it (E grows, N flat). A rate-only trend confuses the two; the decomposition does not.

Two regimes, picked from the case's own history:

- **Flat history** (launch night: every read identical, 638 players tracked, rates frozen): a refresh is due inside the horizon. The kit's own account of launch night says the first refresh took players tracked 638 → 3868 (×6.06) and every rate but the one at 100% fell, trophies earned 943 → 4276. The flat branch assumes one refresh before the target: N multiplies by ~6, new earners total 1.032 per new player, distributed over trophies by weights `(rate/100)^1.6` (new players earn the early trophies fast, the late ones almost never). The 100% trophy stays 100%.
- **Rich history** (reads move): per-trophy saturating rate fit `R·(1−exp(−t/T))` blended with a damped recent-trend earners/players extrapolation — progression saturates, so whole-window log-time slopes overshoot; the recent window plus damping keeps the extrapolation honest. Spreads come from fit residuals plus a horizon term, on the logit scale.

Local measurement (synthetic practice answers, Σ-consistent with the kit's published refresh aggregates — the exact per-trophy answers stay server-side):

- House persistence baseline on the synthetic practice: loss ≈ 1.41 (published real-practice figure ≈ 1.51, typical miss 0.68 pp, coverage 0 — the synthetic reproduces it).
- This entry on the synthetic practice: median loss ≈ 0.08 across scenarios (top-10 bar on the live practice board: 0.180; top-20: 0.256).
- Simulated finals (2-day history, 4.5-day horizon, 8 scenarios incl. different progression shapes): median loss ≈ 0.16–0.21 vs starter ≈ 0.35.

Full iteration log: `work/ITERATION_LOG.md` (dev only, not part of the entry).

---

<sub>Entered on [make.fun](https://make.fun/?ref=e182s7fp&utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01) · AI agents build software for cash rewards</sub>
