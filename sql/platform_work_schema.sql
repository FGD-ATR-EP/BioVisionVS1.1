CREATE TABLE IF NOT EXISTS workstreams (
    workstream_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'in_progress', 'blocked', 'done')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS epics (
    epic_id TEXT PRIMARY KEY,
    workstream_id TEXT NOT NULL REFERENCES workstreams(workstream_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'in_progress', 'blocked', 'done')),
    target_date DATE
);

CREATE TABLE IF NOT EXISTS stories (
    story_id TEXT PRIMARY KEY,
    epic_id TEXT NOT NULL REFERENCES epics(epic_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    persona TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'in_progress', 'blocked', 'done'))
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL REFERENCES stories(story_id) ON DELETE CASCADE,
    task_name TEXT NOT NULL,
    measurable_ac TEXT NOT NULL,
    owner TEXT,
    estimate_points INTEGER CHECK (estimate_points >= 0),
    status TEXT NOT NULL CHECK (status IN ('todo', 'doing', 'blocked', 'done'))
);

CREATE TABLE IF NOT EXISTS architecture_options (
    option_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    tradeoffs TEXT NOT NULL,
    is_selected BOOLEAN NOT NULL DEFAULT FALSE,
    rationale TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS risks (
    risk_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    failure_mode TEXT NOT NULL,
    impact TEXT NOT NULL,
    likelihood TEXT NOT NULL,
    mitigation_plan TEXT NOT NULL,
    owner TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rollout_plans (
    plan_id TEXT PRIMARY KEY,
    phase_name TEXT NOT NULL,
    owner TEXT NOT NULL,
    timeline_window TEXT NOT NULL,
    success_gate TEXT NOT NULL,
    rollback_steps TEXT NOT NULL
);
