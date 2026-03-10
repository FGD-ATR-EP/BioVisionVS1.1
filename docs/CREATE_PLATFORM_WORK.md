# BioVisionNet Platform Work Plan

## Initiative Context
- **Initiative**: INSPIRAFIRMA / AETHERIUM-GENESIS — BioVisionNet platform hardening.
- **Scope**: model modules (`src/models`), CLI service (`main.py`), reliability/ops artifacts (`docs`, `sql`).
- **Drivers**: reliability, latency stability for temporal inference, reproducibility, operator readiness.
- **Current State**: single temporal strategy (`mean`) and roadmap-only planning for systemized platform work.
- **Target State**: configurable temporal backends + structured production work plan + database schema for execution tracking.
- **Constraints**: maintain compatibility with existing inference flow, Python-only runtime, low integration complexity.
- **Dependencies**: model maintainers, data pipeline owners, MLOps/infra for deployment and dashboards.

## 1) Workstreams
1. **Architecture**
   - Introduce pluggable temporal backend in model construction.
   - Keep classifier dimension-safe across backends.
2. **Protocol**
   - Add CLI contract: `--temporal_backend {mean,lstm,transformer}`.
   - Define persistence contract for work tracking and rollout states.
3. **Reliability**
   - Add unit coverage for each temporal backend.
   - Validate tensor shape consistency for 5D temporal inputs.
4. **Benchmark**
   - Compare latency and memory for mean/lstm/transformer on identical frame sequences.
   - Define acceptance thresholds per backend.
5. **Ops**
   - Produce rollout/rollback procedure and ownership map.
   - Add production Definition of Done checklist.
6. **Migration**
   - Default remains `mean`; new backends are opt-in.
   - No breaking checkpoint format change for existing mean model use.

## 2) Backlog (Epic → Story → Task with measurable acceptance criteria)

### Epic A — Temporal Backend Extensibility
- **Story A1**: As an ML engineer, I can select temporal behavior without editing model source.
  - Task A1.1: Implement `TemporalProcessingAdapter` with `mean`, `lstm`, `transformer` modes.
    - **AC**: adapter raises `ValueError` for unsupported backend; outputs rank-2 embedding `[B, D]` for sequence input.
  - Task A1.2: Wire backend selection to `BioVisionNetV1_1S` and classifier.
    - **AC**: forward pass succeeds for all 3 backends with no shape mismatch.

### Epic B — Interface and Configuration Contract
- **Story B1**: As an operator, I can choose backend from CLI.
  - Task B1.1: Add `--temporal_backend` argument.
    - **AC**: CLI help displays allowed values; model initialization receives user selection.

### Epic C — Validation and Reliability
- **Story C1**: As QA, I can verify backend behavior with automated tests.
  - Task C1.1: Add unit tests for adapter outputs and model forward compatibility.
    - **AC**: tests assert output dimensions for each backend and pass in CI/local runs.

### Epic D — Platform Execution Structure
- **Story D1**: As platform lead, I can track rollout and risk execution using structured storage.
  - Task D1.1: Add normalized SQL schema for workstreams, epics/stories/tasks, options, risks, and rollout plans.
    - **AC**: schema applies cleanly in PostgreSQL-compatible engines without syntax errors.

## 3) Options, Tradeoffs, and Recommendation

### Option 1 — Keep Mean Pooling Only
- **Pros**: lowest latency, minimal code complexity.
- **Cons**: weak temporal expressiveness, limited research flexibility.

### Option 2 — Add LSTM Only
- **Pros**: strong temporal memory with moderate complexity.
- **Cons**: recurrent bottleneck; less parallelism than transformer.

### Option 3 — Add Pluggable Mean + LSTM + Transformer (**Chosen**)
- **Pros**: best flexibility; enables benchmark-driven selection by environment.
- **Cons**: larger test matrix and configuration surface.

**Reason chosen**: aligns with roadmap goal while preserving backward compatibility (default `mean`).

## 4) Risks, Failure Modes, Mitigation
- **Risk**: Transformer head/dim mismatch causes runtime failure.
  - **Mitigation**: enforce valid parameters in construction and unit tests.
- **Risk**: LSTM backend increases latency beyond SLO.
  - **Mitigation**: benchmark gate before production default changes.
- **Risk**: Configuration drift between environments.
  - **Mitigation**: pin backend in deployment manifests and log selected backend at startup.
- **Failure mode**: sequence length 1 neutralizes temporal gains.
  - **Mitigation**: enforce minimum sequence length policy for temporal deployments.

## 5) Rollout / Rollback Plan
- **Owner**: ML Platform Engineer (implementation), MLOps Engineer (deployment), QA Engineer (validation).
- **Timeline**:
  - Week 1: code + tests + schema.
  - Week 2: benchmark and staging rollout.
  - Week 3: production canary 10% traffic, then 50%, then 100% if SLO passes.
- **Rollout**:
  1. Deploy with default `mean` (no behavior change).
  2. Enable `lstm` in staging; evaluate SLO and quality deltas.
  3. Enable `transformer` for benchmark cohorts only.
- **Rollback**:
  1. Revert runtime config to `mean`.
  2. If needed, redeploy previous image tag.
  3. Archive failing benchmark artifacts and open corrective tasks.

## 6) Production Definition of Done
- **Tests**: unit tests for all backends and forward paths pass.
- **SLO gates**: inference p95 latency and error rate within environment targets.
- **Benchmark gates**: backend comparison report attached with latency/memory/quality metrics.
- **Observability**: logs include selected backend, sequence length, and runtime device.
- **Runbooks**: rollout + rollback playbook published.
- **Security checks**: dependency scan passes and no new critical vulnerabilities.
