#!/bin/bash

# Hasura endpoint and admin secret
HASURA_ENDPOINT="http://localhost:8085/v1/metadata"
ADMIN_SECRET="asi_hasura_admin_secret_2024"

# List of tables to track
TABLES=(
    "sessions"
    "conversations"
    "messages"
    "asi1_messages"
    "api_calls"
    "retry_attempts"
    "orchestrations"
    "tasks"
    "agents"
    "projects"
    "generated_files"
    "websocket_connections"
    "websocket_messages"
    "system_logs"
    "performance_metrics"
    "api_usage"
)

echo "🚀 Tracking tables in Hasura..."

# Track each table
for TABLE in "${TABLES[@]}"; do
    echo "Tracking table: $TABLE"
    curl -X POST $HASURA_ENDPOINT \
        -H "Content-Type: application/json" \
        -H "x-hasura-admin-secret: $ADMIN_SECRET" \
        -d "{\"type\":\"pg_track_table\",\"args\":{\"source\":\"default\",\"schema\":\"public\",\"name\":\"$TABLE\"}}" \
        -s > /dev/null
done

echo "✅ All tables tracked!"

# Set up relationships
echo "🔗 Setting up relationships..."

# Sessions -> Conversations
curl -X POST $HASURA_ENDPOINT \
    -H "Content-Type: application/json" \
    -H "x-hasura-admin-secret: $ADMIN_SECRET" \
    -d '{
        "type": "pg_create_object_relationship",
        "args": {
            "source": "default",
            "table": {"schema": "public", "name": "conversations"},
            "name": "session",
            "using": {"foreign_key_constraint_on": "session_id"}
        }
    }' -s > /dev/null

# Sessions -> Orchestrations
curl -X POST $HASURA_ENDPOINT \
    -H "Content-Type: application/json" \
    -H "x-hasura-admin-secret: $ADMIN_SECRET" \
    -d '{
        "type": "pg_create_array_relationship",
        "args": {
            "source": "default",
            "table": {"schema": "public", "name": "sessions"},
            "name": "orchestrations",
            "using": {
                "foreign_key_constraint_on": {
                    "table": {"schema": "public", "name": "orchestrations"},
                    "column": "session_id"
                }
            }
        }
    }' -s > /dev/null

# Orchestrations -> Tasks
curl -X POST $HASURA_ENDPOINT \
    -H "Content-Type: application/json" \
    -H "x-hasura-admin-secret: $ADMIN_SECRET" \
    -d '{
        "type": "pg_create_array_relationship",
        "args": {
            "source": "default",
            "table": {"schema": "public", "name": "orchestrations"},
            "name": "tasks",
            "using": {
                "foreign_key_constraint_on": {
                    "table": {"schema": "public", "name": "tasks"},
                    "column": "orchestration_id"
                }
            }
        }
    }' -s > /dev/null

# Tasks -> Generated Files
curl -X POST $HASURA_ENDPOINT \
    -H "Content-Type: application/json" \
    -H "x-hasura-admin-secret: $ADMIN_SECRET" \
    -d '{
        "type": "pg_create_array_relationship",
        "args": {
            "source": "default",
            "table": {"schema": "public", "name": "tasks"},
            "name": "generated_files",
            "using": {
                "foreign_key_constraint_on": {
                    "table": {"schema": "public", "name": "generated_files"},
                    "column": "task_id"
                }
            }
        }
    }' -s > /dev/null

echo "✅ Relationships configured!"

# Test the setup
echo "🧪 Testing GraphQL endpoint..."
curl -X POST http://localhost:8085/v1/graphql \
    -H "Content-Type: application/json" \
    -H "x-hasura-admin-secret: $ADMIN_SECRET" \
    -d '{"query":"{ sessions(limit: 1) { session_id } }"}' \
    -s | jq .

echo "🎉 Hasura setup complete!"