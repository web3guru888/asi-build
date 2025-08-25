# Hasura GraphQL Integration Complete! 🚀

## Access Points

### 🌐 Endpoints
- **Hasura Console:** http://localhost:8085/console
- **GraphQL Endpoint:** http://localhost:8085/v1/graphql
- **WebSocket (Subscriptions):** ws://localhost:8085/v1/graphql
- **Admin Secret:** `asi_hasura_admin_secret_2024`

### 🗄️ Database
- **PostgreSQL:** Port 5433
- **Database:** asi_code_db
- **PgAdmin:** http://localhost:5434

## ✅ What's Working

### 1. **Hasura GraphQL Engine**
- Running on port 8085
- Connected to PostgreSQL database
- Real-time subscriptions enabled
- All 15 tables exposed via GraphQL

### 2. **Table Relationships**
All foreign key relationships automatically detected and configured:
- Sessions → Conversations → Messages
- Sessions → Orchestrations → Tasks → Files
- Sessions → Projects → Files
- WebSocket Connections → Messages
- Tasks can have subtasks (self-referential)

### 3. **Real-time Subscriptions**
```graphql
# Watch tasks in real-time
subscription WatchTasks {
  tasks(order_by: {started_at: desc}) {
    task_id
    name
    status
    assigned_agent
  }
}
```

### 4. **Apollo Client Integration**
- Client configured at `/web-ui/apollo-client.ts`
- React components ready at `/web-ui/components/`
- Automatic WebSocket reconnection
- Optimistic caching configured

## 📊 Available GraphQL Operations

### Queries
- `sessions` - Get all session data
- `agents` - List all Kenny agents
- `orchestrations` - View task decompositions
- `tasks` - Get task execution details
- `generated_files` - Access file contents
- `asi1_messages` - Chat history
- `websocket_messages` - WebSocket logs
- `system_logs` - Application logs

### Subscriptions (Real-time)
- Task status updates
- New messages
- Agent activity
- System logs
- Performance metrics

### Mutations
- Update task status
- Create system logs
- Insert performance metrics

## 🔍 Quick Test Queries

### 1. Get Latest Sessions
```graphql
query GetLatestSessions {
  sessions(order_by: {created_at: desc}, limit: 10) {
    session_id
    created_at
    is_active
    conversations_aggregate {
      aggregate { count }
    }
    orchestrations_aggregate {
      aggregate { count }
    }
  }
}
```

### 2. Watch Active Tasks
```graphql
subscription ActiveTasks {
  tasks(where: {status: {_eq: "in_progress"}}) {
    task_id
    name
    assigned_agent
    started_at
  }
}
```

### 3. Get File Contents
```graphql
query GetFiles($projectId: uuid!) {
  generated_files(where: {project_id: {_eq: $projectId}}) {
    file_name
    file_path
    content
    language
    file_size_bytes
  }
}
```

## 🎯 How to Use in Browser

### 1. Open Hasura Console
```bash
open http://localhost:8085/console
```
- Use admin secret: `asi_hasura_admin_secret_2024`
- Explore data in "Data" tab
- Run queries in "API" tab

### 2. Test Subscriptions
In Hasura Console API tab:
```graphql
subscription {
  agents(order_by: {last_active_at: desc}) {
    agent_id
    status
    last_active_at
  }
}
```
Click "Run" and watch real-time updates!

### 3. Integrate in React App
```tsx
import { ApolloProvider } from '@apollo/client';
import apolloClient from './apollo-client';
import TaskMonitor from './components/TaskMonitor';

function App() {
  return (
    <ApolloProvider client={apolloClient}>
      <TaskMonitor orchestrationId="orch_123" />
    </ApolloProvider>
  );
}
```

## 🔗 Integration with ASI-Code Server

The PostgreSQL database is continuously updated by:
- ASI-Code server on port 3333
- Every WebSocket message logged
- All task executions tracked
- File contents stored
- Complete audit trail

## 📈 Performance Features

- **Connection Pooling**: 20 connections max
- **Query Caching**: Enabled in Hasura
- **Multiplexed Subscriptions**: Batch size 100
- **Indexes**: All foreign keys and timestamps indexed

## 🛠️ Docker Commands

```bash
# View Hasura logs
docker logs -f asi-code-hasura

# Restart Hasura
docker-compose -f docker-compose.hasura.yml restart

# Stop Hasura
docker-compose -f docker-compose.hasura.yml down

# Check health
curl http://localhost:8085/healthz
```

## 🎉 Next Steps

1. **Add Authentication**
   - Implement JWT tokens
   - Row-level security
   - User-specific data filtering

2. **Optimize Queries**
   - Add custom resolvers
   - Implement DataLoader pattern
   - Cache heavy queries

3. **Monitoring**
   - Add Hasura Cloud monitoring
   - Set up alerts
   - Track query performance

## 📱 Mobile App Integration
The GraphQL endpoint can be consumed by:
- React Native apps
- Flutter apps
- Native iOS/Android
- Any GraphQL client

## 🔐 Security Notes
- Admin secret in environment variable
- CORS enabled for all domains (restrict in production)
- Anonymous role has read access (restrict in production)

---

**The entire PostgreSQL database is now accessible via GraphQL with real-time subscriptions!** 🚀