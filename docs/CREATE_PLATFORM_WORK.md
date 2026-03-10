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
