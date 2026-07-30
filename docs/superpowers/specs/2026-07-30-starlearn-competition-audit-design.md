# Star-Learn Competition Audit and Remediation Design

Date: 2026-07-30
Status: Approved in brainstorming review
Priority: competition/demo > engineering portfolio > production maturity

## 1. Objective

Star-Learn is an AI education platform covering learner profiles, AI tutoring, Socratic teaching, adaptive learning paths, courses, classrooms, knowledge retrieval, long-term memory, multi-agent orchestration, teacher workflows, and dashboards.

The goal is not to add more features. With more than one month available, the project will be narrowed into a reliable, evidence-based competition entry that supports a live networked demonstration and recorded fallback. The presentation is at least 15 minutes. The narrative priority is:

1. The student's personalized learning loop.
2. Multi-agent technical differentiation.
3. Platform completeness across student and teacher workflows.

The selected strategy is competition-oriented incremental convergence. Keep the FastAPI modular monolith and native HTML/CSS/JavaScript frontend. Do not migrate frontend frameworks or split microservices. Freeze one demonstration path, remove reliability and security blockers, then improve experience, data consistency, and technical communication.

## 2. Audit Scope and Evidence

### 2.1 Scope

The audit covers product value, student and teacher workflows, UX, API boundaries, tutor orchestration, agents, repositories, persistence, external AI services, security, testing, CI, deployment, documentation, and repository hygiene.

### 2.2 Verified facts

- `main.py` is approximately 8,896 lines, with about 306 registered or mounted API routes across `main.py` and `app/api`.
- `db.py` is approximately 5,832 lines; `agents.py` is approximately 1,476 lines.
- Large frontend files include `css/index.css` at about 11,541 lines, `js/index.js` at about 10,416 lines, `css/classroom.css` at about 8,800 lines, and `js/classroom.js` at about 7,770 lines.
- Tests cover backend unit, contract, integration, security, performance, red-team, and smoke concerns, plus Vitest, Playwright, accessibility, and visual regression on the frontend.
- CI currently runs E2E through `npm run test:e2e || echo ...`, so an E2E failure does not fail that step.
- Security infrastructure includes centralized CORS/CSRF handling, request-size limits, security headers, rate limiting, and trace middleware.
- `app/api/auth.py` has a fallback JWT secret; security configuration enables development mode by default; multiple authentication and password-compatibility paths coexist.
- Python execution uses a blacklist plus subprocess timeout. Its own documentation states that it is not suitable for untrusted multi-tenant code.
- Git tracks about 11,698 files, including approximately 9,718 embedded Python runtime files, 226 `node_modules` files, and 47 audio artifacts. Git pack size is about 234 MB.
- The working tree contains extensive user changes. This design does not modify or revert them.

### 2.3 Test evidence limits

A broad backend test run excluding slow, AI, CV, performance, and E2E tests did not complete within 120 seconds. The first confirmed cause of the many setup errors was denial of access to the user temporary directory in the restricted execution environment. These setup errors cannot be attributed to the project. A narrower run passed its first 24 tests and then encountered the same environment limitation.

Frontend Vitest could not load its config because esbuild was denied access while traversing parent directories in the restricted environment. Therefore, this audit does not claim that all backend or frontend tests pass. It also does not count these sandbox permission failures as project defects. A complete baseline must be collected on a normal development machine and in CI.

## 3. Current Assessment

### 3.1 Weighting

Competition and presentation quality account for 65%:

| Dimension | Weight |
|---|---:|
| Educational problem and user value | 15% |
| Personalized learning loop | 15% |
| AI and multi-agent differentiation | 12% |
| Live demo reliability | 12% |
| Product experience and visual consistency | 6% |
| Delivery potential and clarity | 5% |

Engineering portfolio quality accounts for 35%:

| Dimension | Weight |
|---|---:|
| Architecture and maintainability | 8% |
| Data consistency and evolution | 6% |
| Security and authorization | 7% |
| Test and delivery credibility | 6% |
| Observability, performance, reliability | 5% |
| Documentation and repository hygiene | 3% |

### 3.2 Baseline estimate

| Area | Estimate |
|---|---:|
| Competition potential | 7.4/10 |
| Product completeness | 6.8/10 |
| Technical differentiation | 8.2/10 |
| Live demo reliability | 5.8/10 |
| Engineering portfolio quality | 6.3/10 |
| Production maturity | 4.5/10 |
| Weighted overall score | 6.9/10 |

These are static-audit and limited-runtime estimates, not formal benchmark results. Completing P0 and P1 should raise the competition score above 8.5/10.

### 3.3 Strengths

- The conceptual product covers a complete student-teacher-course-classroom landscape.
- AI work goes beyond chat and includes memory, Socratic strategy, supervision, proactive tutoring, and anti-hallucination mechanisms.
- Test categories show awareness of contracts, security, regression, accessibility, and visual quality.
- Design and implementation records are substantial, with recent fixes to authentication, knowledge retrieval, and smoke flows.
- The native frontend has extensive custom design and many demonstrable scenarios.

### 3.4 Critical gaps

- Product scope is too broad, and the educational loop is not yet the sole narrative center.
- Oversized entry files mix application assembly, routing, business behavior, compatibility, and data access.
- ORM, legacy database access, sync and async access, local JSON, and multiple database paths coexist without a sufficiently clear source of truth.
- Authentication entry points, identity derivation, role assignment, and environment defaults require consolidation.
- The current code executor is not a security boundary for untrusted code.
- CI can report success despite E2E failure.
- Dependencies, runtimes, and generated media are committed, increasing repository size and delivery friction.
- Documentation and executable configuration show signs of drift.

## 4. Product Narrative and Demo Path

The presentation must prove more than "the AI can chat." It must show that the system maintains a changing learner state, adapts teaching decisions from evidence, and writes each learning event back into the next student and teacher decision.

Three claims must recur throughout the presentation:

1. The system understands longitudinal learner state, not only the current message.
2. Teaching strategy changes because learning evidence changes, not because of a fixed prompt.
3. Every learning action updates data that affects the next student and teacher action.

The fixed live path is:

```text
Sign in with a seeded demo account
-> inspect the existing learner profile
-> answer a diagnostic question or ask for help
-> identify a weak concept and show the evidence
-> conduct a short Socratic tutoring sequence
-> generate or adjust the personalized learning path
-> complete a micro-exercise
-> show changed mastery, profile, and recommendation
-> open the teacher view and show an intervention recommendation
```

The agent orchestration console is a technical explanation insert, not the main product surface. The teacher view proves that learner evidence feeds teaching decisions; it does not compete with the student story.

## 5. Target Architecture Boundaries

The target remains a modular monolith with six clear boundaries.

### 5.1 Experience layer

The student experience owns diagnosis, tutoring, course learning, exercises, and feedback. The teacher experience owns learner insight and intervention. The competition build exposes a fixed entry and coherent navigation, while hiding incomplete or unrelated pages.

### 5.2 API layer

`main.py` becomes application assembly over time. Demo-path routes move into `app/api/`, with explicit request models, authentication dependencies, and response contracts. Legacy routes remain only as compatibility adapters and receive no new behavior.

### 5.3 Tutor orchestration layer

Tutor Engine is the only entry for the demo teaching process. It performs context aggregation, intent classification, Socratic strategy selection, agent dispatch, output validation, and response composition. Frontend pages, `main.py`, teacher services, and agents must not maintain conflicting teaching decision logic.

### 5.4 Intelligent capability layer

Profiler, Planner, Socratic, Recommend, Critic, and Audit each own one decision category. Agents communicate with structured inputs and outputs. Each run records rationale, duration, provider, trace ID, and fallback state.

### 5.5 Data and memory layer

Repository interfaces are the only demo-path data boundary, with ORM as the target implementation. Legacy `db.py` remains for migration compatibility. Profile, progress, knowledge nodes, conversation memory, learning paths, and teacher insights are associated with one verified user identity.

### 5.6 External service layer

LLM, TTS, ASR, Bilibili, Qdrant, search, and media generation use provider adapters. Each adapter normalizes timeouts, limited retry, short-circuit behavior, caching, errors, and demonstration fallback.

## 6. Reliability and Fallback

### 6.1 Four levels of protection

1. **Real call:** use real LLM, retrieval, and learner state on the primary path. Record time to first token, total latency, provider, and trace ID.
2. **Automatic fallback:** retry an LLM timeout once, then use a backup model or cache. Fall back from Qdrant to structured retrieval. Fall back from TTS/ASR to text.
3. **Seeded demonstration state:** fixed accounts have resettable profiles, weak concepts, courses, paths, and teacher insights. Fallback output is explicitly tagged internally as `fallback`.
4. **Human fallback:** prepare short recordings and screenshots for every critical step. Switch after approximately eight seconds of uninterrupted waiting.

### 6.2 Reliability acceptance criteria

- At least 95% success across 20 consecutive full demo runs.
- Visible feedback within three seconds.
- The core student loop completes within six minutes.
- Failure of a non-core external service cannot break the loop.
- A one-command reset reproduces the expected account and data state.
- Every failure is traceable to API, agent, data, or provider through a trace ID.

## 7. Security Design

The following are P0 for the competition build:

- Refuse startup outside development when a strong random `JWT_SECRET` is not configured; remove the fallback secret.
- Make `/api/auth/*` the only authentication entry. Legacy login endpoints only delegate for compatibility.
- Do not allow public registration to select `teacher` or `admin`; privileged roles are created through controlled administration or seeding.
- Enable demo accounts only through an explicit switch and bind them to a predefined dataset.
- Derive user identity from a verified JWT on all user-data endpoints; never trust a path or body `user_id` for authorization.
- Disable arbitrary code execution in the competition environment. If execution must be demonstrated, use a separate container with read-only filesystem, network isolation, and CPU, memory, process, and time limits.
- Do not skip CSRF origin checks by default in the competition environment.
- Never log passwords, tokens, API keys, or prompts containing complete sensitive learner data.
- Add regression tests for authentication bypass, horizontal privilege escalation, role escalation, and malicious code execution.

## 8. Testing and Delivery

Tests prioritize the live path over superficial coverage metrics.

### 8.1 Required tests

- One happy-path smoke test against the real application server and an isolated database.
- Fallback tests for LLM timeout, SSE interruption, retrieval failure, and database write failure.
- Security tests for login, cross-user access, role escalation, and malicious code.
- Contract tests for profile update, path adjustment, mastery change, and teacher-dashboard synchronization.
- Visual checks at the presentation laptop resolution, backup laptop resolution, and a critical mobile viewport.
- Startup, health, reset, and external dependency checks.

### 8.2 CI rules

- Remove E2E failure swallowing. A core-path failure blocks merge.
- Use isolated temporary databases; tests never modify live demo data.
- Slow, AI, and external media suites may run separately but must report clearly.
- Reports distinguish pass, fail, skip, and external-service fallback.
- Retain the `agents.py` growth guard and add "no new business logic" evolution constraints for `main.py` and `db.py`.

## 9. Competition Scope Decisions

### 9.1 Keep and polish

- Authentication and seeded demo accounts.
- Learner profile and weak-point diagnosis.
- AI tutor and Socratic teaching.
- Personalized learning path.
- Micro-exercise and mastery update.
- Agent rationale and execution trace.
- Teacher insight and intervention recommendation.
- Course content and knowledge citations.

### 9.2 Keep as supporting evidence

- TTS, ASR, and Bilibili import.
- PPT and course generation.
- Data dashboard.
- Long-term memory and knowledge graph.
- Mascot and growth systems.
- Agent orchestration console.

### 9.3 Degrade automatically

- TTS/ASR to text.
- Vector retrieval to structured retrieval.
- Video generation to pre-generated media.
- External search to the local knowledge base.
- Secondary-agent failure to base Tutor Engine policy.

### 9.4 Hide or disable

- Arbitrary code execution without strong isolation.
- Incomplete pages or pages with fabricated/empty data.
- Duplicate authentication entry points.
- Empty dashboards, placeholder actions, and unverifiable AI output.
- Long-running live video generation.
- Experimental pages unrelated to the main learning loop.

## 10. Remediation Roadmap

### 10.1 P0: Week 1, eliminate demo failure modes

- Freeze the demo path, account, and resettable data snapshot.
- Unify identity derivation and fix role escalation and cross-user access.
- Enforce competition security configuration and disable unsafe execution.
- Fix false-green CI and create a real demo smoke test.
- Add timeouts and fallbacks to LLM, retrieval, and media calls.
- Remove 404s, empty states, console errors, and data mismatches from the demo path.
- Provide one-command start, reset, and health checks.
- Run and record 20 consecutive demonstrations.

### 10.2 P1: Weeks 2-3, improve competition strength

- Converge the student loop into consistent navigation and visual hierarchy.
- Visualize profile changes, recommendation rationale, and path changes.
- Explain why agents decide, not merely which agent ran.
- Unify frontend API calls, loading, error, and fallback states.
- Move demo routes into the appropriate `app/api/` modules.
- Route demo persistence through repositories.
- Complete contract, security, fallback, and visual tests for the live path.
- Produce the script, architecture diagram, data-flow diagram, recordings, and technical Q&A.

### 10.3 P2: Week 4 and later, strengthen the engineering portfolio

- Continue decomposing `main.py`, `db.py`, and oversized frontend files.
- Converge on ORM and Alembic; retire JSON dual-write and old-table compatibility incrementally.
- Remove tracked runtimes, dependencies, audio, logs, databases, and backups; retain reproducible build scripts.
- Enforce formatting, static checks, dependency audit, and meaningful coverage gates.
- Maintain ADRs, module ownership, deployment runbooks, and failure-drill evidence.
- Validate cross-browser behavior, weak networks, concurrency, and long-running stability.

## 11. Presentation Plan: 15-18 Minutes

| Time | Content | Evidence |
|---|---|---|
| 0:00-1:30 | Educational problem, user, core claim | Not a generic chat wrapper |
| 1:30-3:00 | Learner profile and weakness | Persistent student state |
| 3:00-7:30 | AI tutor and Socratic teaching | Adaptive teaching behavior |
| 7:30-10:00 | Exercise changes profile and path | Closed learning loop |
| 10:00-11:30 | Teacher insight and intervention | Data returns to educators |
| 11:30-14:00 | Agents, memory, knowledge, supervision | Technical differentiation serves pedagogy |
| 14:00-15:30 | Security, explainability, fallback, tests | Credible and reliable delivery |
| 15:30-17:00 | Metrics, deployment scenario, roadmap | Practical potential and boundaries |
| Remaining | Q&A or backup demonstration | Presentation resilience |

Lead with educational value, prove it through the product, and use architecture to support technical questions. Architecture terminology cannot replace observable user outcomes.

## 12. Technical Q&A Preparation

Prepare evidence-based answers for at least these questions:

- How are agents different from a conventional prompt chain?
- Which events update the learner profile, and how is error accumulation controlled?
- Why did the learning path change, and can the rationale be reproduced?
- What belongs in long-term memory, the relational database, and the vector store?
- How are hallucination, prompt injection, and malicious input handled?
- Can the teaching loop finish when an external model fails?
- How is student data isolated between teachers and users?
- How is code execution isolated, and why is the current implementation disabled?
- What concurrency can the system support, and where are the bottlenecks?
- Why not split microservices or migrate the frontend now?
- Which features are real-time capabilities and which are fallback demonstrations?
- How does CI prove that the main path has not regressed?

Answers should point to traces, tests, before/after data, or module boundaries rather than concepts alone.

## 13. Definition of Done

Competition remediation is complete only when:

- The fixed path connects the student experience to the teacher experience.
- Learning state visibly changes before and after the exercise.
- Twenty runs meet the reliability target, with timing and failure categories recorded.
- Core security checks pass: no fallback secret, privileged self-registration, or horizontal privilege escalation.
- Unsafe code execution is disabled or replaced by strong isolation.
- Core CI cannot swallow failures and does not touch demo data.
- External service failures have automatic and recorded-video fallback.
- Demo accounts reset in one command and dependencies pass a preflight health check.
- The 15-18 minute script, recordings, architecture diagram, and Q&A have been rehearsed.
- Documentation distinguishes real capability, fallback capability, and future plans without overstating production maturity.

## 14. Explicit Non-Goals

- No React, Vue, or other frontend framework migration.
- No microservice split.
- No production-grade completion of every page.
- No long-running live video generation during the presentation.
- No use of coverage percentage as a substitute for demo-path validation.
- No complete deletion of all legacy APIs or persistence compatibility before the competition.
- No new features unrelated to the personalized learning loop.

These constraints protect delivery certainty and match the agreed priority of competition success first and engineering portfolio quality second.
