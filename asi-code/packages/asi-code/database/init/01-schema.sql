-- ASI-Code Comprehensive Database Schema
-- Stores ALL platform data including chat history, ASI1 interactions, tasks, logs, etc.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==========================================
-- SESSIONS & USERS
-- ==========================================

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_sessions_session_id ON sessions(session_id);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
CREATE INDEX idx_sessions_active ON sessions(is_active);

-- ==========================================
-- ASI1 CHAT HISTORY
-- ==========================================

CREATE TABLE asi1_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    conversation_id VARCHAR(255) UNIQUE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    total_messages INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    model_used VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active', -- active, completed, error
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE asi1_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES asi1_conversations(id) ON DELETE CASCADE,
    message_index INTEGER NOT NULL,
    role VARCHAR(50) NOT NULL, -- system, user, assistant
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text', -- text, code, json
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_asi1_messages_conversation ON asi1_messages(conversation_id);
CREATE INDEX idx_asi1_messages_sent_at ON asi1_messages(sent_at);
CREATE INDEX idx_asi1_messages_role ON asi1_messages(role);

-- ==========================================
-- ASI1 API CALLS
-- ==========================================

CREATE TABLE asi1_api_calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES asi1_conversations(id) ON DELETE SET NULL,
    request_id VARCHAR(255) UNIQUE,
    endpoint VARCHAR(255),
    method VARCHAR(10),
    request_body JSONB,
    request_headers JSONB,
    response_status INTEGER,
    response_body JSONB,
    response_headers JSONB,
    response_time_ms INTEGER,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    api_key_used VARCHAR(100), -- Hashed/partial key for tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_asi1_api_calls_created_at ON asi1_api_calls(created_at);
CREATE INDEX idx_asi1_api_calls_status ON asi1_api_calls(response_status);
CREATE INDEX idx_asi1_api_calls_session ON asi1_api_calls(session_id);

-- ==========================================
-- ORCHESTRATION & TASKS
-- ==========================================

CREATE TABLE orchestrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    orchestration_id VARCHAR(255) UNIQUE NOT NULL,
    task_description TEXT NOT NULL,
    original_request TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, decomposing, executing, completed, failed
    total_subtasks INTEGER DEFAULT 0,
    completed_subtasks INTEGER DEFAULT 0,
    estimated_hours DECIMAL(10, 2),
    actual_hours DECIMAL(10, 2),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    orchestration_id UUID REFERENCES orchestrations(id) ON DELETE CASCADE,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    parent_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    task_type VARCHAR(100), -- architecture, backend, frontend, database, security, testing, deployment
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, completed, failed, cancelled
    assigned_agent VARCHAR(255),
    can_parallel BOOLEAN DEFAULT false,
    dependencies JSONB DEFAULT '[]'::jsonb,
    estimated_hours DECIMAL(10, 2),
    actual_hours DECIMAL(10, 2),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    result TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_tasks_orchestration ON tasks(orchestration_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_agent ON tasks(assigned_agent);
CREATE INDEX idx_tasks_parent ON tasks(parent_task_id);

-- ==========================================
-- AGENTS
-- ==========================================

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(100), -- supervisor, specialist, worker
    capabilities JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(50) DEFAULT 'idle', -- idle, busy, offline
    current_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    total_tasks_completed INTEGER DEFAULT 0,
    total_tasks_failed INTEGER DEFAULT 0,
    average_completion_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_type ON agents(agent_type);

-- ==========================================
-- GENERATED PROJECTS & FILES
-- ==========================================

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    orchestration_id UUID REFERENCES orchestrations(id) ON DELETE CASCADE,
    project_name VARCHAR(500) NOT NULL,
    project_type VARCHAR(100), -- web, mobile, android, ios, api, cli, library
    framework VARCHAR(100),
    language VARCHAR(100),
    output_path TEXT,
    total_files INTEGER DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,
    features JSONB DEFAULT '[]'::jsonb,
    dependencies JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE generated_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    file_path TEXT NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_extension VARCHAR(50),
    file_size_bytes BIGINT,
    content TEXT, -- Store actual file content
    content_hash VARCHAR(64), -- SHA256 hash for deduplication
    language VARCHAR(100),
    purpose TEXT,
    generation_method VARCHAR(50), -- asi1, template, mock
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_generated_files_project ON generated_files(project_id);
CREATE INDEX idx_generated_files_task ON generated_files(task_id);
CREATE INDEX idx_generated_files_hash ON generated_files(content_hash);
CREATE INDEX idx_generated_files_extension ON generated_files(file_extension);

-- ==========================================
-- WEBSOCKET CONNECTIONS & EVENTS
-- ==========================================

CREATE TABLE websocket_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    connection_id VARCHAR(255) UNIQUE NOT NULL,
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    disconnected_at TIMESTAMP WITH TIME ZONE,
    total_messages_sent INTEGER DEFAULT 0,
    total_messages_received INTEGER DEFAULT 0,
    ip_address INET,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE websocket_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connection_id UUID REFERENCES websocket_connections(id) ON DELETE CASCADE,
    direction VARCHAR(10) NOT NULL, -- inbound, outbound
    message_type VARCHAR(100),
    message_data JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ws_messages_connection ON websocket_messages(connection_id);
CREATE INDEX idx_ws_messages_timestamp ON websocket_messages(timestamp);
CREATE INDEX idx_ws_messages_type ON websocket_messages(message_type);

-- ==========================================
-- SYSTEM LOGS & EVENTS
-- ==========================================

CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_level VARCHAR(20) NOT NULL, -- debug, info, warn, error, fatal
    source VARCHAR(255), -- component/module name
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}'::jsonb,
    stack_trace TEXT,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_logs_level ON system_logs(log_level);
CREATE INDEX idx_system_logs_source ON system_logs(source);
CREATE INDEX idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX idx_system_logs_session ON system_logs(session_id);

-- ==========================================
-- RATE LIMITING & API USAGE
-- ==========================================

CREATE TABLE api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_key_hash VARCHAR(64) NOT NULL,
    endpoint VARCHAR(255),
    usage_date DATE NOT NULL,
    request_count INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    rate_limit_hits INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(api_key_hash, endpoint, usage_date)
);

CREATE INDEX idx_api_usage_date ON api_usage(usage_date);
CREATE INDEX idx_api_usage_key ON api_usage(api_key_hash);

-- ==========================================
-- RETRY & ERROR TRACKING
-- ==========================================

CREATE TABLE retry_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type VARCHAR(50) NOT NULL, -- asi1_call, task_execution, file_generation
    source_id UUID,
    attempt_number INTEGER NOT NULL,
    delay_ms INTEGER,
    error_message TEXT,
    success BOOLEAN DEFAULT false,
    attempted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_retry_attempts_source ON retry_attempts(source_type, source_id);
CREATE INDEX idx_retry_attempts_time ON retry_attempts(attempted_at);

-- ==========================================
-- METRICS & ANALYTICS
-- ==========================================

CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255) NOT NULL,
    metric_value DECIMAL(20, 4),
    metric_unit VARCHAR(50),
    tags JSONB DEFAULT '{}'::jsonb,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_name ON performance_metrics(metric_name);
CREATE INDEX idx_metrics_time ON performance_metrics(recorded_at);
CREATE INDEX idx_metrics_tags ON performance_metrics USING gin(tags);

-- ==========================================
-- FUNCTIONS & TRIGGERS
-- ==========================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_usage_updated_at BEFORE UPDATE ON api_usage
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate project statistics
CREATE OR REPLACE FUNCTION update_project_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE projects 
    SET 
        total_files = (SELECT COUNT(*) FROM generated_files WHERE project_id = NEW.project_id),
        total_size_bytes = (SELECT COALESCE(SUM(file_size_bytes), 0) FROM generated_files WHERE project_id = NEW.project_id)
    WHERE id = NEW.project_id;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_project_stats_on_file_insert 
    AFTER INSERT OR UPDATE OR DELETE ON generated_files
    FOR EACH ROW EXECUTE FUNCTION update_project_stats();

-- ==========================================
-- VIEWS FOR COMMON QUERIES
-- ==========================================

CREATE VIEW v_active_sessions AS
SELECT 
    s.*,
    COUNT(DISTINCT o.id) as total_orchestrations,
    COUNT(DISTINCT c.id) as total_conversations,
    COUNT(DISTINCT w.id) as total_connections
FROM sessions s
LEFT JOIN orchestrations o ON s.id = o.session_id
LEFT JOIN asi1_conversations c ON s.id = c.session_id
LEFT JOIN websocket_connections w ON s.id = w.session_id
WHERE s.is_active = true
GROUP BY s.id;

CREATE VIEW v_task_performance AS
SELECT 
    assigned_agent,
    COUNT(*) as total_tasks,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_completion_seconds,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_tasks
FROM tasks
WHERE started_at IS NOT NULL
GROUP BY assigned_agent;

CREATE VIEW v_api_usage_summary AS
SELECT 
    usage_date,
    SUM(request_count) as total_requests,
    SUM(token_count) as total_tokens,
    SUM(error_count) as total_errors,
    SUM(rate_limit_hits) as total_rate_limits
FROM api_usage
GROUP BY usage_date
ORDER BY usage_date DESC;