# NEXT TURN — SUBMIT (turn 2)

Competition: **gta6-trophy-rarity-forecast-01** — "Forecast how many GTA VI
players earn each trophy in week one", $250 pot, FREE.
Deadline: **21 Nov 2026 18:30 WIB** (2026-11-21T11:30:00Z). Result due 2026-12-10.
Entry title: **"Earners-over-players decomposition with refresh prior and
shrunk Theil-Sen trends"** (pick this or a distinct equivalent at submit time).

## Repo

- https://github.com/ipaludhi/gta6-trophy-rarity-forecast (created after the
  2026-11-19T11:30Z opening, public, owner ipaludhi)
- Commit: local HEAD 845200b2824597fffb413ebf869e4e73f1b1c560, remote
  190c95546f2f4eca0bb0fc4fc42fd24df9ccf721 (differs by the seed parent only;
  tree SHA d2db10ea079f5198d12a3f3a499ef3ebb2856234 identical, verified by
  credential-less clone 2026-11-19 ~19:16 WIB; .makefun/owner.json present).
- Files: `main.py` (entry, stdlib only), `README.md`, `LICENSE` (MIT),
  `.makefun/owner.json` (payout wallet 3EJmUxUZZXLXjVpRG6uXBSG7n9kDSBgLVbgnNQDTkgct).
- Secret grep before push: 0 hits (api key / secret / token / private / seed /
  mnemonic / password / bearer).

## Turn-1 evidence (2026-11-19 ~19:15 WIB)

- Kit: `~/workspace/makefun/gta6-trophy-rarity-forecast-01/kit/gta6-trophy-rarity-forecast-01-kit/`
  (RULES.txt + competition.yaml + starter read in full; program/v1 harness).
- Leaderboard bars (live API, 117 ranked, metric `loss`): top-1 0.114 ·
  **top-10 0.180** · top-20 0.256 · median field 0.698. House persistence
  baseline on real practice ≈ 1.51.
- Practice (flat branch), synthetic Σ-consistent answers: **median loss
  0.0703**, miss 0.004–0.005 pp, coverage 1.000. Stress (5 Σ-consistent
  shapes): median 0.073, worst 0.173 — inside the top-10 bar on the
  calibrated synthetic. Honest caveat: the synthetic shares the forecaster's
  model family, so the real server score will be higher; the submit IS the
  real measurement.
- Simulated finals (rich branch, E1 ensemble + dedup), 10 scenarios across
  progression shapes exp/hyp/log, adoption 1.2–1.8, refresh 2–8 h,
  progression 0.6–1.5: **median 0.159, worst 0.208, 9/10 inside top-10**;
  starter 0.32–0.46 on the same cases.
- CLI end-to-end on the real kit input: two runs byte-identical
  (sha256 p00.out = p01.out = 553ffaa35f71c2bbba17d2fa53b10bf28eeb91019c68da4373000d6c07362048),
  68 ms for both cases, 55 rows, ids 1–55, monotone quantiles in [0,100],
  2775 bytes per case (cap 65536).
- Quota (CLI status, ~19:10 WIB): **can submit YES**, 0 entries made,
  10 left today, 20 under hard limit.
- Full iteration log: `work/ITERATION_LOG.md` (dev only, not in repo).
- Kit check: NOT yet run — the bundle is built in this turn (turn 2), then
  `node cli/makefun.mjs check --kit . --repo <repo dir> --transcripts <bundle>`
  from the kit dir. Must pass before submit.

## Submit steps (turn 2 only, in this side chat)

1. `node cli/makefun.mjs status --competition gta6-trophy-rarity-forecast-01`
   — re-check can_submit YES and quota before spending anything.
2. Bundle with the strict recipe (AGENTS.md / ~/memory/mistakes.md 2026-11-19):
   real system prompt file (~/workspace/system/system_prompt.md) +
   instructions collected (omit --instructions) + muse.db usage rows
   (--muse-usage) + parent chain via --parent-session with --no-family +
   prompt = ipal's verbatim message (prompt-user.txt, byte-exact from the
   main-chat session file). Never withheld:/none.
3. Kit check (above). Fix only if it fails on a real defect; do not redesign.
4. Submit ONCE via the kit CLI submit command. Save the receipt:
   submission id + claim code (claim code ONLY in this side chat, never in
   MEMORY.md or main chat). Never claim automatically.
5. Report the submit result to main chat (submission id + that the real
   practice score is now measurable on the leaderboard). Then read the
   leaderboard: if the practice score lands outside top 20, iterate only if
   a provably better version exists (Force_Last is permanent; resubmit only
   if provably MUCH better + can_submit true + deadline not passed).
