# NEXT — what to do first, in order

Updated: 2026-09-08 · This file is a QUEUE. The spec log it used to be lives in
[`archive/NEXT-specs-2026-08.md`](archive/NEXT-specs-2026-08.md) (every user quote verbatim,
indexed) and [`archive/NEXT-log.md`](archive/NEXT-log.md). When an item here closes, delete it
and note the closure in the ledger files — this file holds no history.

His standing order (2026-09-08): go over the whole project again; **own generated models are
sanctioned** where they buy honest hitboxes; adapt the docs so they help; keep iterating.

---

## The queue

1. **Own-model generator** — design scouted 2026-09-08 (round live). Models authored AROUND
   their hit geometry dissolve the drawn≠registered class at the root: per-kind titan bodies
   (five kinds share one slab-shaped glb today), the cloth-less banner, the worst mis-centred
   remnants. **Must also cover ANIMATION authoring** — the pack ships zero clips, so titans
   stand instead of walking and the sword swing has no motion (archive §2B).
2. **Forward cut arc** (archive §2H, FIND-127): the blade is cast at 90° from view — the steel
   leaves the frame on exactly the ticks that can hit. Re-measures f030/q030 evidence when it
   lands. Strongest surviving cause of his *"attack fehlt aber noch"*.
3. **F-060 guard rule, deliberately withheld** (archive §2F, FIND-123): one `matches!` in
   `receive_hits`; landing it reddens q030/q031/f030 rows that open the warden via their own
   torso graze. Order: re-aim those to open the guard explicitly → land the rule → re-measure
   the 0.15 m nape margin (currently an upper bound, not a fact).
4. **Traversal/lane ruling — HIS** (archive §2G + FIND-229): gantries replace/keep/accept-slow,
   AND the measured new fact that river tower body 79 at 345 m outcompetes the lane beam.
   f025-chain, f004-towers, w5-lane re-pins all wait on this one ruling.
5. **Sky and fog** (archive §1F-4): still ClearColor. The fallen-ring mood is fog+light more
   than geometry; cheapest big look win after the wall re-cut.
6. **B-045**: game-full's two rope reds (slack rope moves a standing player 9.7 m/s; 16 m/s at
   release after a full stop) — needs a rope-domain owner, numbers are in the entry.
7. **Speed-envelope drift attribution** (FIND-230): f-001-hooks says 12/14, measures 10/14;
   w5 gallery lines drifted. Attribute against gravity −32 / B-040 pull / §5D before any re-pin.
8. **B-046**: f177 board-prompt flake (~1 in 5) — find the writer, prove with 30 greens.
9. **B-014 one-rope gas** (rule 1 distance-gate) and **B-021 energy sink** — the two old
   movement-economy bugs, both with full entries.
10. **F-028 fallback feedback** check (archive §2A): with the marker assembly deleted (FIND-227),
    what tells the player WHY no hook fired? Verify against the current HUD before building.
11. **Bellower** (archive §2E): max_spawnable_class cap + FIND-118 diff + F-051 gas noise.
12. **Small chores**: f030_* registry tests → T-id rename (archive §1E-3a) · t075-*.png renames
    (§1E-3b) · settings.rs:59 "Half-angle" + menu settings.rs:99 "deg max" label checks (§2D) ·
    grounded-steer gas bill (§1C-1, vector→player edge decision).
13. **Multiplayer replication** and **sound** (his files) — deliberately later; rule 4 keeps the
    architecture ready.

## His open decisions (docs/QUESTIONS.md has the full entries)

- **Q-086 elevation**: 24 (shipped ASSUMPTION) vs 48 — four photographs in
  `docs/images/f003-field-*.png`; any number works, `max_rise_m ≥ 1.32×` and `base_m` move with it.
- **Lane ruling** (item 4 above) — three options, measured numbers in archive §2G.
- **Playtest-gated**: Q-063 gravity feel · Q-064 Shift · Q-046 gas costs · Q-077/Q-080 rope feel ·
  B-020 three husks · the §5D W-angle trade.

## Standing state (2026-09-08 evening)

Corpus 67 GREEN / 15 RED / 0 CRASH — the model swap moved zero scripts; every red is the
attributed drift-debt stack riding on items 4 and 7 above (lane ruling + speed envelope).
Full suite green (25 binaries). Pushed through `d609e52`.

## §6A — his 2026-09-08 test-suite verdict, verbatim, and it gets an instrument

> *"ein problem das ich onch sehe sind zu viele unnötigen tests die vermutlich so aufgebaut
> sind, dass diese so oder so durchlaufen und nicht wirklich intensiv testen ob systeme
> richtig laufen!"*

He is measurably right at least once already: the two-arm blend guard passed the whole
suite under a blend-destroying mutation (FIND-226 amendment) until an adversary proved it.
The claim generalizes and gets the only honest instrument, in two passes:
1. **Static vacuity sweep (read-only, runs now):** candidates by pattern — one-sided
   bounds where the two-sided rule applies, asserts on what the fixture itself set,
   brackets wide enough to pass any plausible value, tests with no behavioural assert,
   near-duplicates. Output: a ranked candidate list with file:line, no deletions.
2. **Mutation kill-matrix (after the model wave lands — rebuilds would poison its runs):**
   ~20-30 one-line semantic breaks across the core systems (gates deleted, signs flipped,
   scales zeroed — the `blend = direction` shape), each rebuilt and run against the
   binaries that CLAIM to cover the file (+ --lib). A test that catches no mutation of its
   own system is vacuous (strengthen or delete); a mutation no test catches is a coverage
   hole (new test). The matrix is the deliverable; the suite shrinks or sharpens from
   EVIDENCE, never from taste.

His second half, minutes later, verbatim:

> *"und diese tests die in angesporchen habe gehen immer recht lang und halten langzeitig
> das projekt stark auf! eine idee wäre es in libs zu arbeiten oder die tests zu separieren
> damit man dadurch nicht aufgehalten wird und unabhänig einfach und schnell testen kann!"*

3. ~~Speed pass~~ **DONE 2026-09-08 evening (FIND-237)**: two tiers, one binary — fast
   suite ~105 s (was ~648), inner loop per touched binary 3–11 s, `--full` once at the
   push gate, guard test against tier abuse. Consolidation 22→7 and the workspace split
   stay queued behind their FIND-236 triggers. Original scope: the suite is 181 s best-case
   and the distribution is extreme — one binary (vector_rope) runs 385 s, the top four
   carry ~90 % of the runtime, and each of the 25 integration binaries pays its own full
   link of the game. Two levers, in order of cheapness: (a) TIERING — slow sim-heavy tests
   behind `#[ignore]` with a gate-only full tier, plus consolidating the many tiny
   binaries (each is a link); (b) THE WORKSPACE SPLIT he proposes — rule 3 already
   enforces domain boundaries, so per-domain crates (`cargo test -p vector`) are the
   architecture's own next step, not a rewrite. A scout measures the real costs (link vs
   run per binary, cross-domain type knots like shared/data) before anything moves.
