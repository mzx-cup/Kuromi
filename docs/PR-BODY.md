# PR Body — P1 Close-out

> Ready-to-paste body for the eventual PR against `origin/main`.
> All work is currently on local `main`; the user/team will branch and push as desired.

---

## Title

`feat(p1): close S1–S6 gaps + advance S7–S12 to testable state`

## Summary

- **Phase A (S1–S6 gap closure):** Citation-position validation (G-class red-team hardening), env-flag dual-rail dispatch in `SocraticEvaluatorAgent.run()`, real `MemoryCardLoader` with per-field fetchers + TTL cache, real LLM-backed `extract_pattern` with per-cluster timeout.
- **Phase B (S7–S12 close-out):** Supervision escalation chain + ActionLedger cooldown + channel-dispatcher exponential backoff, drift detection (file hash + ADR + TTL + APScheduler cron), Socratic/Profile/Echo memory-card schemas with isolation, Claude `SessionStart` 5-source parallel loader producing a ≤ 3KB state card, chaos drill script + 213-prompt red-team suite (`overall_pass=True`), 555-line P1 runbook.

10 commits, each tagged `slice-A1..A4`, `slice-B1..B6`. Total diff: **54 files, +5411 / -41 lines**.

## What's changed

| Slice | Files | Lines |
|-------|-------|-------|
| A1 cite position | `citation_position.py` + test | 74 + 36 |
| A2 dispatch fix | `agents.py` (dispatch block) | +32 net |
| A3 memory card | `card_cache.py` + `field_fetchers.py` + `memory_card_loader.py` + tests | 30+128+212+72 |
| A4 LLM extract | `llm_extractor.py` + test | 166 |
| B1 supervision | `escalation_chain.py` + conftest + tests + `rule_engine.py` (shadowing-bug fix) | 65+28+248+217+241 |
| B2 drift | 4 new modules + `drift_report.py` + 130-line CLI | 100s |
| B3 parity | `langchain_parity.py` + 8-case e2e | 230+203 |
| B4 profile/echo | 2 schemas + test | 50+38 |
| B5 claude card | 3 modules + test + `.claude/settings.json` | 90+45 |
| B6 chaos + runbook | `chaos_drill.py` + 100 new prompts + 555-line runbook | 342+127+555 |

## Test Plan

- [ ] `pytest tests/services/ tests/integration/ tests/parity/` — 232 passed, 9 supervision passed, 1 skipped (env-only), 4 parity SKIPPED until conversations.jsonl is populated. Expected ≥ 270 passed.
- [ ] `PYTHONPATH=. python tests/redteam/run.py` — 213 prompts, `overall_pass=True`, all 8 categories at 1.0 safe_fallback ratio.
- [ ] `python scripts/chaos_drill.py` — `PASS: 0, SKIP: 3, FAIL: 0` in dev sandbox (docker daemon absent). Production staging should yield `PASS: 3, SKIP: 0`.
- [ ] Manual `USE_LANGCHAIN_SOCRATIC=1 pytest tests/integration/test_anti_hallucination_e2e.py -v` — 6/6 PASS confirms the new path actually invokes `produce_socratic_response` (verify with `mock_p.called == True`).
- [ ] Run new `SliceStart` hook in a real Claude-Code session (Windows or Linux) and confirm markdown output under 3KB and P95 latency under 2s.

## Spec / Plan references

- Spec: `docs/superpowers/specs/2026-07-16-s1s6-gap-and-rollout-design.md`
- Plan: `docs/superpowers/plans/2026-07-16-s1s6-gap-and-rollout.md`
- Slice ledger: `docs/SUMMARY.md` §2

## Risks & Rollback

- **Risk:** `MemoryCardLoader._ensure_fetchers` defaults to empty repos. Without the post-merge follow-up to wire real ORM repos, agent memory cards return placeholder strings in production.
- **Risk:** Daily cron jobs (drift + memory consolidation) are wired to APScheduler factories but not `.start()`-ed from `main.py:lifespan`. Production deployments must call those on startup.
- **Risk:** `USE_LANGCHAIN_SOCRATIC=1` exercises the new LangChain path. Default is `=0` (legacy), so existing callers are untouched.
- **Rollback:** `READ_BACKEND_PERCENTAGE=0` + `DUAL_WRITE_LEGACY=true` reverts the broader read path; `unset USE_LANGCHAIN_SOCRATIC` reverts the Socratic dual-rail. The pre-A2 `agents.py` is recoverable via `git revert a657594` since each slice is independently git-tagged.

## Follow-ups (separate issues)

Tracked in `docs/SUMMARY.md` §6:

1. Fill `tests/parity/conversations.jsonl` `a_langchain` rows.
2. Wire `start_drift_scheduler()` + `start_consolidation_scheduler()` in `main.py:lifespan`.
3. Wire `FieldFetchers(repos=...)` with the 4 real ORM repos.
4. Add P99 < 3s perf assertion for SocraticAgent.
5. Add `灰度` rollout section to `docs/runbook-p1.md`.
6. Add a CI regression test enforcing `agents.py` ≤ 50 lines net per PR.
7. Verify `.claude/settings.json` SessionStart hook on a live Claude-Code session.
