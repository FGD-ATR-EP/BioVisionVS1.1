CREATE TABLE workstreams (
    workstream_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    owner TEXT,
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'active', 'blocked', 'completed')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE epics (
    epic_id SERIAL PRIMARY KEY,
    workstream_id INTEGER NOT NULL REFERENCES workstreams(workstream_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE stories (
    story_id SERIAL PRIMARY KEY,
    epic_id INTEGER NOT NULL REFERENCES epics(epic_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    acceptance_criteria TEXT,
    status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'done')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE tasks (
    task_id SERIAL PRIMARY KEY,
    story_id INTEGER NOT NULL REFERENCES stories(story_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    assignee TEXT,
    due_date DATE,
    status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'done', 'blocked')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE architecture_options (
    option_id SERIAL PRIMARY KEY,
    workstream_id INTEGER REFERENCES workstreams(workstream_id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    summary TEXT NOT NULL,
    pros TEXT,
    cons TEXT,
    decision TEXT CHECK (decision IN ('proposed', 'selected', 'rejected')) DEFAULT 'proposed'
);

CREATE TABLE risks (
    risk_id SERIAL PRIMARY KEY,
    workstream_id INTEGER REFERENCES workstreams(workstream_id) ON DELETE SET NULL,
    risk_description TEXT NOT NULL,
    failure_mode TEXT,
    likelihood TEXT CHECK (likelihood IN ('low', 'medium', 'high')),
    impact TEXT CHECK (impact IN ('low', 'medium', 'high')),
    mitigation_plan TEXT
);

CREATE TABLE rollout_plans (
    rollout_id SERIAL PRIMARY KEY,
    workstream_id INTEGER REFERENCES workstreams(workstream_id) ON DELETE SET NULL,
    phase_name TEXT NOT NULL,
    owner TEXT,
    timeline_start DATE,
    timeline_end DATE,
    rollback_plan TEXT,
    gate_criteria TEXT
);

CREATE INDEX idx_epics_workstream_id ON epics(workstream_id);
CREATE INDEX idx_stories_epic_id ON stories(epic_id);
CREATE INDEX idx_tasks_story_id ON tasks(story_id);
CREATE INDEX idx_rollout_plans_workstream_id ON rollout_plans(workstream_id);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_epics_updated_at
BEFORE UPDATE ON epics
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_stories_updated_at
BEFORE UPDATE ON stories
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_tasks_updated_at
BEFORE UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
