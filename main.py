"""GTA VI trophy rarity forecaster (make.fun gta6-trophy-rarity-forecast-01).

Reads one case (/input/<id>.in: every Exophase read of the game's PS5 trophy
page before the checkpoint) and writes /output/<id>.out: for each of the 55
trophies, five quantiles (5/25/50/75/95%) of its earn rate at the target.

Model: earners-over-players decomposition, r = E / N.
  - E_i(t): players tracked who have earned trophy i (rate_i * N / 100).
  - N(t): players tracked.
  Both are forecast separately and divided, because a trophy's rate moves for
  two different reasons: new players joining dilute it (N jumps at an Exophase
  refresh, E barely moves) while players progressing raise it (E grows, N
  flat). A rate-only trend confuses the two; the decomposition does not.

Two regimes, picked from the case's own history:
  - FLAT history (every read identical): the launch-night shape. Exophase had
    not refreshed yet, so the history carries no trend at all -- but a refresh
    is due inside the horizon, and when it lands the tracked population jumps
    and every rate falls. The kit's own account of launch night (competition
    .yaml / RULES.txt) says the first refresh took players tracked 638 -> 3868
    (x6.06) and every rate but the one at 100% fell, while trophies earned went
    943 -> 4276. The flat branch therefore assumes one refresh before the
    target: N multiplies by ~6, and each trophy's new earners follow a
    power law in its current rate (new players earn the early trophies fast and
    the late ones almost never), q_i = (r_i/100)^1.6, the exponent fitted to
    the kit's published aggregates (sum of earners 4276). The 100% trophy
    stays 100%: every new player earns it immediately.
  - RICH history (reads move): ensemble of two medians, averaged in logit
    space -- (a) a per-trophy saturating rate fit r(t) = R*(1-exp(-t/T)),
    T grid-searched, because trophy shares saturate; (b) a damped
    recent-trend earners/players extrapolation (Theil-Sen slopes of log E
    and log N over the last 24 h, shrunk toward the cross-trophy median
    slope, excess over the players slope damped by half). Whole-window
    log-time slopes overshoot badly past saturation, so they are not used.
    Spread is the max of the two components' residual spreads plus a
    horizon term, floored and capped so a flat trophy still carries
    honest doubt.

Spreads are on the logit scale, widening with horizon, so the 5-95 band is an
honest 90% interval: too narrow pays for every trophy outside it, too wide
pays at every trophy (pinball loss is a proper scoring rule).

Deterministic: no randomness, no wall clock, no network, sorted iteration
only. Standard library only; runs in well under the 8 s cap.
"""

import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]
RELEASE = "2026-11-19T00:00:00Z"  # release day began, UTC (case game.release_date)

# --- flat-branch priors (kit-published launch-night refresh) -----------------
FLAT_N_JUMP = 6.06      # first refresh: players tracked 638 -> 3868
FLAT_POWER = 1.6        # new-player earn curve w_i = (r_i/100)^1.6: new players
                        # earn the early trophies fast, the late ones almost
                        # never (exponent fitted to the kit's published
                        # aggregates; see below)
FLAT_NEW_PER_PLAYER = 1.032  # mean trophies a new player holds at the refresh:
                        # trophies earned 943 -> 4276 over 3230 new players
                        # (kit's published aggregates). The new earners are
                        # distributed over trophies by w_i, normalised so their
                        # total is exactly dN * FLAT_NEW_PER_PLAYER.
FLAT_SIGMA = 0.30       # logit spread while a refresh is pending (tuned, see
                        # work/ITERATION_LOG.md; median across Sigma-consistent
                        # practice-answer shapes, worst case as tiebreak)
FLAT_SIGMA_LONG = 0.60  # same, when the horizon is over 12 h (more can move)

# --- rich-branch tuning -------------------------------------------------------
SHRINK_W = 0.65         # weight of a trophy's own Theil-Sen slope vs the
                        # cross-trophy median slope
DAMP = 0.5              # damping of the excess slope over the players slope
                        # (component B): progression saturates
SIGMA_FLOOR = 0.30      # minimum logit spread (a flat trophy still moves)
SIGMA_CAP = 1.60        # maximum logit spread
RESID_SCALE = 1.4826    # MAD -> sigma
HORIZON_SIGMA = 0.10    # extra logit spread per sqrt(day) of horizon, for
                        # refresh timing the history cannot see


def clamp_pct(x):
    return min(99.99, max(0.01, x))


def logit(pct):
    p = clamp_pct(pct) / 100.0
    return math.log(p / (1.0 - p))


def inv_logit(lg):
    if lg >= 0:
        return 100.0 / (1.0 + math.exp(-lg))
    e = math.exp(lg)
    return 100.0 * e / (1.0 + e)


def round4(x):
    scaled = x * 10000
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 10000
    return int(value) if value == int(value) else value


def parse_ts(s):
    """ISO 8601 UTC -> epoch seconds (no datetime tz surprises)."""
    # '2026-11-19T03:00:00Z' or with fractional seconds.
    date, _, time = s.partition("T")
    y, mo, d = (int(v) for v in date.split("-"))
    time = time.rstrip("Z")
    if "." in time:
        time, frac = time.split(".")
        frac_s = float("0." + frac)
    else:
        frac_s = 0.0
    h, mi, sec = (int(v) for v in time.split(":"))
    days = _days_from_civil(y, mo, d)
    return days * 86400 + h * 3600 + mi * 60 + sec + frac_s


def _days_from_civil(y, m, d):
    """Days since 1970-01-01 (Howard Hinnant's algorithm)."""
    y -= 1 if m <= 2 else 0
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    mp = (m + 9) % 12
    doy = (153 * mp + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    if n % 2:
        return s[n // 2]
    return 0.5 * (s[n // 2 - 1] + s[n // 2])


def theil_sen(xs, ys):
    """Median pairwise slope; robust to the step jumps a refresh causes."""
    n = len(xs)
    if n < 2:
        return 0.0
    slopes = []
    for i in range(n):
        for j in range(i + 1, n):
            dx = xs[j] - xs[i]
            if dx > 1e-9:
                slopes.append((ys[j] - ys[i]) / dx)
    if not slopes:
        return 0.0
    return median(slopes)


def forecast_case(case, name):
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    history = case["history"]
    if not history:
        raise ValueError(f"{name} has no history")
    trophies = case["trophies"]
    horizon_h = case["horizon_minutes"] / 60.0
    t_release = parse_ts(case["game"].get("release_date", "2026-11-19") + "T00:00:00Z")
    t_target = parse_ts(case["target"])
    last = history[-1]
    n_last = last["players_tracked"]
    # Dedup: the house records the page every 10 min, but Exophase only
    # refreshes its counts hours apart, so most consecutive reads are the
    # SAME page repeated. Identical repeats carry no information and break
    # pairwise estimators (Theil-Sen on step data collapses toward the
    # zero slope of intra-step pairs). Collapse consecutive reads with
    # identical players_tracked and rates into one state, keeping the first
    # timestamp that showed it. The flat branch still sees a 1-state history.
    deduped = []
    for read in history:
        key = (read["players_tracked"], tuple(read["rates"]))
        if deduped and deduped[-1][1] == key:
            continue
        deduped.append((read, key))
    history = [r for r, _ in deduped]

    rates_last = last["rates"]

    # Hours since release for every read, and per-trophy earners E_i(t).
    # Prefer the read's clock slot (exact); fall back to its read time.
    times_h = []
    ns = []
    earners = [[] for _ in trophies]  # earners[i][k]
    for read in history:
        stamp = read.get("slot") or read["at"]
        t = (parse_ts(stamp) - t_release) / 3600.0
        times_h.append(t)
        n = read["players_tracked"]
        ns.append(n)
        for i in range(len(trophies)):
            r = read["rates"][i]
            if r is None:
                earners[i].append(None)
            else:
                earners[i].append(max(0.0, r * n / 100.0))

    # Regime: flat when nothing ever moved (same N and same rates throughout).
    flat = all(n == ns[0] for n in ns) and all(
        all(
            (e is None and earners[i][0] is None) or (e == earners[i][0])
            for e in earners[i]
        )
        for i in range(len(trophies))
    )

    rows = []
    if flat:
        rows = _forecast_flat(trophies, rates_last, n_last, horizon_h)
    else:
        rows = _forecast_rich(
            trophies, times_h, ns, earners, history, t_target, t_release, horizon_h
        )
    return {"trophies": rows}


def _quantiles(median_rate, sigma):
    """Five quantiles around a median rate, logit-normal spread sigma."""
    if median_rate >= 100.0:
        # Universal trophy: everyone holds it; only a hair of lower tail.
        qs = [99.5, 99.9, 100.0, 100.0, 100.0]
        return [round4(q) for q in qs]
    lg = logit(median_rate)
    qs = []
    for z in Z:
        qs.append(round4(clamp_pct(inv_logit(lg + z * sigma))))
    # Enforce non-decreasing after rounding.
    for k in range(1, 5):
        if qs[k] < qs[k - 1]:
            qs[k] = qs[k - 1]
    return qs


def _forecast_flat(trophies, rates_last, n_last, horizon_h):
    """One refresh pending: N jumps, new players earn on a power-law curve.

    New earners total dN * FLAT_NEW_PER_PLAYER, distributed by weights
    w_i = (r_i/100)**FLAT_POWER, so the forecast respects the published
    refresh aggregates whatever the exponent. The 100% trophy's weight (1.0)
    dominates the normalisation, so it keeps ~all new players and stays 100%.
    """
    sigma = FLAT_SIGMA if horizon_h <= 12.0 else FLAT_SIGMA_LONG
    n_new = n_last * FLAT_N_JUMP
    d_n = n_new - n_last
    weights = []
    for i in range(len(trophies)):
        r = rates_last[i]
        if r is None:
            r = 0.0
        weights.append((r / 100.0) ** FLAT_POWER if r > 0 else 0.0)
    w_sum = sum(weights) or 1.0
    total_new = d_n * FLAT_NEW_PER_PLAYER
    rows = []
    for i, trophy in enumerate(trophies):
        r = rates_last[i]
        if r is None:
            r = 0.0
        if r >= 100.0:
            rows.append({"id": trophy["id"], "q": _quantiles(100.0, sigma)})
            continue
        e_old = r * n_last / 100.0
        e_new = total_new * weights[i] / w_sum
        med = 100.0 * (e_old + e_new) / n_new
        rows.append({"id": trophy["id"], "q": _quantiles(med, sigma)})
    return rows


def _subsample_pairs(xs, ys, k=48):
    """Evenly thin (x, y) points to at most k, for O(n^2) Theil-Sen speed."""
    if len(xs) <= k:
        return xs, ys
    idx = sorted({round(i * (len(xs) - 1) / (k - 1)) for i in range(k)})
    return [xs[i] for i in idx], [ys[i] for i in idx]


def _theil_sen_fast(xs, ys):
    xs2, ys2 = _subsample_pairs(xs, ys)
    return theil_sen(xs2, ys2)


def _rich_trend(trophies, times_h, x, x_target, ns, earners, horizon_h):
    """Component B: damped recent-trend earners/players extrapolation.

    Slopes from the last 24 h only (the current regime, not the launch
    surge), shrunk toward the cross-trophy median slope, with the excess
    over the players slope damped by DAMP: progression saturates, so the
    recent velocity overstates a 4.5-day move. Returns per trophy
    (median_rate, sigma).
    """
    log_n = [math.log(max(1.0, n)) for n in ns]
    t_last = times_h[-1]
    recent = [i for i, t in enumerate(times_h) if t >= t_last - 24.0]
    if len(recent) < 3:
        recent = list(range(len(times_h)))
    xr = [x[i] for i in recent]
    s_n = _theil_sen_fast(xr, [log_n[i] for i in recent])
    icept_n = median([y - s_n * xi for xi, y in zip(x, log_n)])
    log_n_star = icept_n + s_n * x_target
    log_n_star = max(log_n[-1], min(log_n_star, log_n[-1] + math.log(50.0)))
    n_star = math.exp(log_n_star)
    resid_n = [y - (icept_n + s_n * xi) for xi, y in zip(x, log_n)]
    sig_n = RESID_SCALE * median([abs(v - median(resid_n)) for v in resid_n])

    slopes = []
    fits = []
    for i in range(len(trophies)):
        rpts = [(x[k], math.log(max(0.5, earners[i][k])))
                for k in recent if earners[i][k] is not None]
        pts = [(x[k], math.log(max(0.5, e)))
               for k, e in enumerate(earners[i]) if e is not None]
        use = rpts if len(rpts) >= 2 else pts
        if len(use) < 2:
            slopes.append(0.0)
            fits.append(None)
            continue
        xs_i = [p[0] for p in use]
        ys_i = [p[1] for p in use]
        slopes.append(_theil_sen_fast(xs_i, ys_i))
        fits.append((xs_i, ys_i, slopes[-1]))
    med_s = median(slopes)

    out = []
    for i, trophy in enumerate(trophies):
        last_e = earners[i][-1] or 0.0
        fit = fits[i]
        if fit is None:
            e_star, sigma = last_e, max(SIGMA_FLOOR, sig_n)
        else:
            xs_i, ys_i, s = fit
            s_sh = SHRINK_W * s + (1.0 - SHRINK_W) * med_s
            s_sh = s_n + DAMP * (s_sh - s_n)
            s_sh = max(0.0, s_sh)
            icept = median([y - s_sh * xi for xi, y in zip(xs_i, ys_i)])
            log_e = icept + s_sh * x_target
            log_e = max(math.log(max(0.5, last_e)), min(log_e, log_n_star))
            e_star = math.exp(log_e)
            resid = [y - (icept + s_sh * xi) for xi, y in zip(xs_i, ys_i)]
            mad = median([abs(v - median(resid)) for v in resid])
            sigma = min(SIGMA_CAP, max(SIGMA_FLOOR, RESID_SCALE * mad + sig_n))
        med = 100.0 * e_star / n_star if n_star > 0 else 0.0
        sigma = min(SIGMA_CAP, sigma + HORIZON_SIGMA * math.sqrt(horizon_h / 24.0))
        out.append((med, sigma))
    return out


def _rich_saturating(trophies, times_h, history, t_target_h, horizon_h):
    """Component C: per-trophy saturating rate fit r(t) = R*(1-exp(-t/T)).

    T grid-searched per trophy (least squares); R fit by least squares for
    each T. Trophy shares saturate -- a rate cannot grow forever -- so this
    is the right shape for week-one progression. Returns per trophy
    (median_rate, sigma).
    """
    out = []
    for i, trophy in enumerate(trophies):
        rs = []
        ts = []
        for k, read in enumerate(history):
            r = read["rates"][i]
            if r is not None:
                rs.append(r)
                ts.append(times_h[k])
        if len(rs) < 2:
            out.append((rs[-1] if rs else 0.0, SIGMA_FLOOR))
            continue
        best = None
        for T in (6, 12, 24, 48, 96, 192, 384, 768, 10 ** 9):
            fs = [1.0 - math.exp(-max(0.0, t) / T) if T < 1e8 else 1.0 for t in ts]
            den = sum(f * f for f in fs)
            R = sum(r * f for r, f in zip(rs, fs)) / den if den > 0 else 0.0
            R = max(0.0, min(100.0, R))
            sse = sum((r - R * f) ** 2 for r, f in zip(rs, fs))
            if best is None or sse < best[0]:
                best = (sse, R, T)
        _, R, T = best
        f_tgt = 1.0 - math.exp(-max(0.0, t_target_h) / T) if T < 1e8 else 1.0
        med = R * f_tgt
        resid = []
        for r, t in zip(rs, ts):
            f = 1.0 - math.exp(-max(0.0, t) / T) if T < 1e8 else 1.0
            resid.append(logit(max(0.01, r)) - logit(max(0.01, R * f)))
        sig = RESID_SCALE * median([abs(v - median(resid)) for v in resid]) if resid else 0.5
        sig = min(SIGMA_CAP, max(0.35, sig + HORIZON_SIGMA * math.sqrt(horizon_h / 24.0)))
        out.append((med, sig))
    return out


def _forecast_rich(trophies, times_h, ns, earners, history, t_target, t_release, horizon_h):
    """Ensemble E1: logit-mean of the saturating fit (C) and the damped
    recent-trend earners/players extrapolation (B); sigma = max of the two.

    Each component alone overshoots on some progression shapes; their mean
    is the most robust median across shapes (median loss 0.169, worst 0.211
    over 8 simulated finals incl. exp/hyp/log progression, vs 0.186/0.215
    for C/B alone and ~0.35 for the house baseline). See work/ITERATION_LOG.md.
    """
    x = [math.log1p(max(0.0, t)) for t in times_h]
    x_target = math.log1p(max(0.0, (t_target - t_release) / 3600.0))
    t_target_h = max(0.0, (t_target - t_release) / 3600.0)
    comp_b = _rich_trend(trophies, times_h, x, x_target, ns, earners, horizon_h)
    comp_c = _rich_saturating(trophies, times_h, history, t_target_h, horizon_h)
    rows = []
    for i, trophy in enumerate(trophies):
        med_b, sig_b = comp_b[i]
        med_c, sig_c = comp_c[i]
        med = inv_logit(0.5 * (logit(med_b) + logit(med_c)))
        sigma = max(sig_b, sig_c)
        rows.append({"id": trophy["id"], "q": _quantiles(med, sigma)})
    return rows


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        out = OUTPUT_DIR / f"{path.stem}.out"
        out.write_text(json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
