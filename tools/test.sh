#!/usr/bin/env bash
# test.sh — run the test suite so that a runaway test dies ALONE.
#
# 🔴 Why this exists, measured 2026-09-01 (`B-030`, `FIND-218`): `tests/vector_hooks.rs`
# ordered a system in `SimulationSystems::World` `.after(aim)` while `aim` had moved to
# `SimulationSystems::PostStep`. The six stages are `.chain()`ed, so that closed a dependency
# cycle in `FixedUpdate` — and bevy answers a cycle by enumerating EVERY simple cycle in the
# component and formatting all of them into one `String`
# (`bevy_ecs-0.19.0/src/schedule/error.rs:174`). Here: **2 290 028 cycles**, a single `realloc`
# of **4 966 055 936 bytes**, `total-vm 81 GB / anon-rss 25 GB`, and the kernel's OOM killer
# took the user's whole tmux session down with the test binary.
#
# The one-line mistake is fixed. The SHAPE is not: any future cycle in any schedule does the
# same thing, and the number is combinatorial in the size of the strongly connected component,
# not in anything a reviewer can eyeball. So the suite runs under a hard per-process address
# limit. A runaway then hits `memory allocation of N bytes failed` and dies alone.
#
#   tools/test.sh                       # FAST tier: --lib plus every integration binary
#   tools/test.sh --lib --test world    # the round-gate cut: pass cargo's own args
#   tools/test.sh --full                # FULL tier — the push gate (FIND-236)
#   DBT_TEST_CAP_KB=8388608 tools/test.sh   # a bigger cap, if a test really needs it
#
# 🔴 TWO TIERS, ONE BINARY SET (FIND-236, measured 2026-09-08): the whole suite costs
# ~648 s and four binaries carry 602 s of it (vector_rope 385 · titan 88 · player 76 ·
# mission 53 — ~1 812 full-city App startups inside five matrix tests). The expensive
# tests are `#[ignore = "full tier: …"]`; libtest skips them by default, so the FAST tier
# (no flag, projected 60–90 s) is what every round runs. `--full` appends
# `-- --include-ignored --skip measure_ --skip probe_` to the RUN half only — the same
# binaries, now with the full-tier tests in and the measurement/probe tests still out —
# and it runs ONCE, at the push gate that closes a round. The compile half is shared:
# ignored tests are compiled either way, so `--full` never rebuilds anything.
# `tests/domains.rs` guards the contract: every `#[ignore]` reason starts with
# "full tier:" or the fn is a measure_/probe_ — the tier is not where tests go to die.
# ⚠️ Do not mix `--full` with your own `-- <libtest args>` section: the flags above are
# appended after yours in that case, which is fine for filters but easy to misread.
#
# 🔴 AND THE ORDER OF THE TWO HALVES IS THE POINT — do not "simplify" it back into one
# command. `ulimit -v` applies to every child, and **`mold` reserves 8 GB of virtual memory
# up front**: under a 6 GB cap the LINKER dies, not the test, with
# `mold: cannot reserve 8589934592 bytes of virtual memory` — a link error wearing a memory
# error's clothes. Measured the same morning, on the very invocation that was supposed to be
# the safe one. So: **compile uncapped, run capped.**
set -u
cd "$(dirname "$0")/.." || exit 1

CAP_KB="${DBT_TEST_CAP_KB:-6291456}"          # 6 GiB of address space per test process
FULL=0
ARGS=()
for a in "$@"; do
  if [ "$a" = "--full" ]; then FULL=1; else ARGS+=("$a"); fi
done
[ ${#ARGS[@]} -gt 0 ] || ARGS=()

# `--full` touches the RUN half only — ignored tests compile either way, the compile
# half stays shared between the tiers. RUN_EXTRA carries its own `--` unless the caller
# already opened a libtest section of their own.
RUN_EXTRA=()
if [ "$FULL" -eq 1 ]; then
  case " ${ARGS[*]-} " in
    *" -- "*) RUN_EXTRA=(--include-ignored --skip measure_ --skip probe_) ;;
    *)        RUN_EXTRA=(-- --include-ignored --skip measure_ --skip probe_) ;;
  esac
fi

echo "== compiling (uncapped: mold needs 8 GB of VM to link) =="
log=$(mktemp -t dbt-test-XXXXXX.log)
nice -n 15 ionice -c 3 cargo test --no-run -j 3 "${ARGS[@]}" >"$log" 2>&1
rc=$?
grep -E '^error' "$log" | head -20
if [ $rc -ne 0 ]; then
  echo "COMPILE FAILED (exit $rc) — nothing was run; full log: $log"
  exit $rc
fi

# 🔴 ONE run, not two. `cargo test` is 181 s at best here, so re-running it just to read `$?`
# is the exact waste `CLAUDE.md` bans. The status comes out of `${PIPESTATUS[0]}` — the FIRST
# command of the pipeline — because a pipeline's own `$?` is the LAST command's and `grep`
# succeeds whenever it matched anything at all.
tier=fast; [ "$FULL" -eq 1 ] && tier=full
echo "== running, ${tier} tier (ulimit -v ${CAP_KB} KB per process) =="
# ⚠️ NO DBT_SAVE_DIR here, and that is a decision with a test behind it: a test binary already
# refuses a save directory on its own (`save::file::in_a_test_binary` detects `target/*/deps`),
# and `a_test_binary_does_not_get_a_save_directory` PINS that. Exporting a scratch dir from here
# overrode the refusal and turned that guard's assertion vacuous — measured 2026-09-01, it went
# red the first run. The processes that really do write the player's save are SCRIPT runs of the
# real binary, and `tools/corpus.sh` isolates those per run (B-036).
( ulimit -v "$CAP_KB"; nice -n 15 ionice -c 3 cargo test -j 3 "${ARGS[@]}" "${RUN_EXTRA[@]}" 2>&1 ) | tee "$log" \
  | grep -E '^test result|^error|panicked|FAILED|memory allocation|does not build'
rc=${PIPESTATUS[0]}
echo "== exit $rc  (full log: $log) =="
exit $rc
