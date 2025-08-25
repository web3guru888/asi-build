# ASI-Code PostgreSQL Database Schema

## Overview
The ASI-Code platform uses PostgreSQL to store ALL platform data including chat history, generated files, orchestrations, and system logs.

## Database Connection
- **Host:** localhost
- **Port:** 5433
- **Database:** asi_code_db
- **User:** asi_admin
- **Password:** asi_secure_pass_2024

## Complete Schema Documentation

### 1. 📊 SESSIONS Table
Tracks every user connection to the platform.

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'
);
```

**Data Stored:**
- Every WebSocket connection
- User IP addresses and browser info
- Session activity tracking
- Custom metadata

---

### 2. 🤖 AGENTS Table
Stores all Kenny agents registered in the system.

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(100),
    capabilities JSONB DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'idle',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP
);
```

**Data Stored:**
- 9 Kenny agents (supervisor, specialists, workers)
- Agent capabilities and status
- Activity tracking

---

### 3. 💬 ASI1_CONVERSATIONS Table
Tracks all conversations with ASI:One API.

```sql
CREATE TABLE asi1_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    conversation_id VARCHAR(255) UNIQUE NOT NULL,
    model_used VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    total_messages INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);
```

**Data Stored:**
- Conversation sessions with ASI1
- Model used (asi1-mini, etc.)
- Token usage tracking

---

### 4. 📝 ASI1_MESSAGES Table
Stores complete message history with ASI:One.

```sql
CREATE TABLE asi1_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES asi1_conversations(id),
    message_index INTEGER NOT NULL,
    role VARCHAR(50) NOT NULL, -- system, user, assistant
    content TEXT NOT NULL,
    tokens_used INTEGER,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored:**
- **FULL MESSAGE CONTENT** - Every chat message
- Token counts for billing
- Message ordering

---

### 5. 🔌 ASI1_API_CALLS Table
Logs every API call to ASI:One.

```sql
CREATE TABLE asi1_api_calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    conversation_id UUID REFERENCES asi1_conversations(id),
    request_id VARCHAR(255) UNIQUE,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    request_body JSONB,
    response_status INTEGER,
    response_body JSONB,
    response_time_ms INTEGER,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored:**
- Complete request/response bodies
- Response times and status codes
- Error messages and retry attempts

---

### 6. 🎯 ORCHESTRATIONS Table
Tracks task decomposition and orchestration.

```sql
CREATE TABLE orchestrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    orchestration_id VARCHAR(255) UNIQUE NOT NULL,
    task_description TEXT NOT NULL,
    original_request TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    total_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);
```

**Data Stored:**
- Every orchestration request
- Task descriptions and status
- Progress tracking

---

### 7. ✅ TASKS Table
Individual tasks within orchestrations.

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    orchestration_id UUID REFERENCES orchestrations(id),
    task_id VARCHAR(255) UNIQUE NOT NULL,
    parent_task_id UUID REFERENCES tasks(id),
    name VARCHAR(500) NOT NULL,
    description TEXT,
    task_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    assigned_agent VARCHAR(255),
    can_parallel BOOLEAN DEFAULT false,
    dependencies JSONB DEFAULT '[]',
    estimated_hours NUMERIC(10,2),
    actual_hours NUMERIC(10,2),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);
```

**Data Stored:**
- Task decomposition details
- Agent assignments
- Dependencies and parallelization
- Execution results

---

### 8. 📁 PROJECTS Table
Generated projects metadata.

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    orchestration_id UUID REFERENCES orchestrations(id),
    project_name VARCHAR(500) NOT NULL,
    project_type VARCHAR(100),
    framework VARCHAR(100),
    language VARCHAR(100),
    output_path TEXT,
    total_files INTEGER DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,
    features JSONB DEFAULT '[]',
    dependencies JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);
```

**Data Stored:**
- Project configurations
- Technology stack
- Features and dependencies

---

### 9. 📄 GENERATED_FILES Table
**STORES COMPLETE FILE CONTENTS!**

```sql
CREATE TABLE generated_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id),
    task_id UUID REFERENCES tasks(id),
    file_path TEXT NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_extension VARCHAR(50),
    file_size_bytes INTEGER,
    content TEXT,  -- FULL FILE CONTENT STORED HERE!
    content_hash VARCHAR(64),  -- SHA256 for deduplication
    language VARCHAR(100),
    purpose TEXT,
    generation_method VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored:**
- **COMPLETE FILE CONTENTS** - Every generated file
- File paths and metadata
- Content hashes for deduplication
- Generation method (asi1, template, etc.)

---

### 10. 🔗 WEBSOCKET_CONNECTIONS Table
Tracks all WebSocket connections.

```sql
CREATE TABLE websocket_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    connection_id VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    disconnected_at TIMESTAMP,
    total_messages_sent INTEGER DEFAULT 0,
    total_messages_received INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);
```

**Data Stored:**
- Every WebSocket connection
- Connection duration
- Message counts

---

### 11. 📨 WEBSOCKET_MESSAGES Table
**STORES ALL WEBSOCKET MESSAGES!**

```sql
CREATE TABLE websocket_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connection_id UUID REFERENCES websocket_connections(id),
    direction VARCHAR(20) NOT NULL, -- 'inbound' or 'outbound'
    message_type VARCHAR(100),
    message_data JSONB,  -- FULL MESSAGE CONTENT!
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored:**
- **EVERY WebSocket message** - inbound and outbound
- Message types and payloads
- Complete audit trail

---

### 12. 📊 SYSTEM_LOGS Table
Comprehensive application logging.

```sql
CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_level VARCHAR(20) NOT NULL,
    source VARCHAR(255),
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    stack_trace TEXT,
    session_id UUID REFERENCES sessions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored:**
- All system logs (info, warning, error)
- Stack traces for errors
- Contextual data

---

### 13. 🔄 RETRY_ATTEMPTS Table
Tracks all retry attempts for rate limiting.

```sql
CREATE TABLE retry_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type VARCHAR(100) NOT NULL,
    source_id UUID,
    attempt_number INTEGER NOT NULL,
    delay_ms INTEGER,
    error_message TEXT,
    success BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored:**
- Exponential backoff attempts
- Error messages
- Success/failure tracking

---

### 14. 📈 API_USAGE Table
API usage tracking and rate limiting.

```sql
CREATE TABLE api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_key_hash VARCHAR(64) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    usage_date DATE NOT NULL,
    request_count INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    rate_limit_hits INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(api_key_hash, endpoint, usage_date)
);
```

**Data Stored:**
- API key usage (hashed)
- Daily usage statistics
- Rate limit tracking

---

### 15. ⚡ PERFORMANCE_METRICS Table
System performance tracking.

```sql
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255) NOT NULL,
    metric_value NUMERIC,
    metric_unit VARCHAR(50),
    tags JSONB DEFAULT '{}',
    session_id UUID REFERENCES sessions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Stored:**
- Response times
- System metrics
- Performance data

---

## 📊 Database Views

### v_active_sessions
Shows currently active sessions with details.

### v_task_performance
Task execution performance metrics.

### v_api_usage_summary
Aggregated API usage statistics.

---

## 🔍 Indexes
- All primary keys have btree indexes
- Foreign keys are indexed
- Timestamp columns indexed for fast queries
- Status fields indexed for filtering

---

## 🔒 Data Retention
- No automatic deletion configured
- All data persisted indefinitely
- Manual cleanup possible via SQL

---

## 📈 Current Statistics
```sql
SELECT 
  (SELECT COUNT(*) FROM sessions) as sessions,
  (SELECT COUNT(*) FROM asi1_messages) as messages,
  (SELECT COUNT(*) FROM tasks) as tasks,
  (SELECT COUNT(*) FROM generated_files) as files,
  (SELECT COUNT(*) FROM orchestrations) as orchestrations,
  (SELECT COUNT(*) FROM websocket_messages) as ws_messages;
```

## 🚀 Key Points
1. **FULL CONTENT STORAGE** - Messages, files, logs stored completely
2. **COMPLETE AUDIT TRAIL** - Every action tracked
3. **NO DATA LOSS** - Everything persisted to PostgreSQL
4. **SEARCHABLE** - All content indexed and queryable
5. **SCALABLE** - Designed for millions of records