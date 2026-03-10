# CREATE_PLATFORM_WORK

## Initiative Context
- **Initiative**: BioVisionNet Platform Reliability and Temporal Intelligence
- **Scope**: CLI entrypoint, temporal modeling module, persistence schema, and release operations.
- **Drivers**: reliability, latency stability for sequence inference, maintainability, and developer experience.
- **Current state**: Temporal flow is configurable in model code and CLI; project-level platform planning docs were missing.
- **Target state**: Single source of truth planning document with workstreams, measurable acceptance criteria, rollout/rollback controls, and production DoD.
- **Constraints**: Ship within one release cycle, preserve backward compatibility with default mean backend, maintain offline/local execution.
- **Dependencies**: ML engineering, data platform (SQL schema owners), DevOps release support.

## Workstreams
1. **Architecture**: Temporal backend abstraction and model contract hardening.
2. **Protocol**: CLI/runtime interface for backend selection and validation.
3. **Reliability**: Shape safety, invariant checks, and failure-mode handling.
4. **Benchmark**: Backend comparison for quality/latency/memory.
5. **Ops**: Runbooks, observability fields, release gates.
6. **Migration**: Adoption plan from mean-only behavior to configurable backends.

## Backlog (Epic → Story → Task)

### Epic A: Temporal Backend Productization
- **Story A1**: As an operator, I can choose temporal aggregation at runtime.
  - Task A1.1: Add `--temporal_backend` CLI flag with constrained choices.
  - Task A1.2: Wire CLI value to `BioVisionNetV1_1S` constructor.
  - **Acceptance criteria**: Running CLI with each supported backend initializes model without code changes.
- **Story A2**: As a developer, I get deterministic shape contracts across backends.
  - Task A2.1: Record `temporal.output_dim` and bind classifier input to it.
  - Task A2.2: Update inline docs/comments for backend-agnostic embedding shape.
  - **Acceptance criteria**: For mean/lstm/transformer, logits shape remains `[B, num_classes]` and embedding shape equals `[B, temporal.output_dim]`.

### Epic B: Planning and Delivery Governance
- **Story B1**: As stakeholders, we maintain one complete project plan.
  - Task B1.1: Document workstreams, options, risks, rollout, and DoD in one file.
  - Task B1.2: Remove duplicated planning fragments from scattered notes.
  - **Acceptance criteria**: A single platform work document covers architecture/protocol/reliability/ops/migration decisions.
- **Story B2**: As data consumers, we persist auditable platform work items.
  - Task B2.1: Define normalized SQL schema for workstreams/epics/stories/tasks/options/risks/rollout.
  - Task B2.2: Add timestamps and relational links for traceability.
  - **Acceptance criteria**: Schema includes FK integrity and lifecycle timestamps for execution tracking.

## Options and Tradeoffs
1. **Option 1: Mean only**
   - Pros: lowest latency and complexity.
   - Cons: limited temporal expressiveness.
2. **Option 2: Mean + LSTM (selected for balanced adoption)**
   - Pros: captures sequence order with moderate complexity.
   - Cons: added recurrent overhead.
3. **Option 3: Mean + LSTM + Transformer**
   - Pros: highest modeling flexibility.
   - Cons: head divisibility and memory constraints require stronger validation.

**Recommendation**: Adopt Option 3 with strict constructor validation and default `mean` for backward compatibility.

## Risks, Failure Modes, Mitigation
- **Risk**: Invalid transformer configuration (e.g., non-divisible `input_dim` / `heads`).
  - Failure mode: runtime attention dimension error.
  - Mitigation: fail-fast validation in adapter constructor.
- **Risk**: Output shape mismatch when switching backends.
  - Failure mode: classifier dimension mismatch.
  - Mitigation: use `temporal.output_dim` as classifier input contract.
- **Risk**: Operational confusion during rollout.
  - Failure mode: inconsistent backend usage across environments.
  - Mitigation: explicit CLI flag documentation and release checklist gates.

## Rollout and Rollback Plan
- **Phase 1 (Owner: ML Eng, Week 1)**: release code with default `mean`, keep existing behavior unchanged.
- **Phase 2 (Owner: QA + ML Eng, Week 2)**: enable LSTM/Transformer in staging, run benchmark and regression suite.
- **Phase 3 (Owner: Ops, Week 3)**: production rollout with monitored canary jobs.
- **Rollback**: force `--temporal_backend mean`, redeploy prior model artifact if regression exceeds threshold.

## Definition of Done (Production)
- Tests: unit coverage for invalid backend, 2D passthrough, output_dim, and model integration.
- SLO gates: inference p95 latency and error-rate thresholds unchanged for default backend.
- Benchmarking gates: quality/latency/memory comparison across backends on representative sequences.
- Observability: backend choice logged per run; model/version metadata persisted.
- Runbooks: include backend selection guidance and rollback instructions.
- Security checks: dependency scan clean and no unsafe dynamic execution paths introduced.
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
