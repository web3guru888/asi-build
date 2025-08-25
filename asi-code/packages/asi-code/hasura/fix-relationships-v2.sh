#!/bin/bash

# Fix Hasura Relationships for ASI-Code - Using correct API format
# This script creates all necessary relationships between tables

HASURA_ENDPOINT="http://localhost:8085/v1/metadata"
HASURA_SECRET="asi_hasura_admin_secret_2024"

echo "🔧 Fixing Hasura relationships with correct API..."

# First, reload metadata to ensure all tables are tracked
echo "Reloading metadata..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "reload_metadata",
    "args": {}
  }' 2>/dev/null

echo ""
echo "Creating relationships using pg_ commands..."

# 1. Create relationship: tasks -> orchestration
echo "Creating tasks -> orchestration relationship..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "pg_create_object_relationship",
    "args": {
      "source": "default",
      "table": {
        "schema": "public",
        "name": "tasks"
      },
      "name": "orchestration",
      "using": {
        "foreign_key_constraint_on": "orchestration_id"
      }
    }
  }' 2>/dev/null | jq '.message // .'

# 2. Create relationship: orchestrations -> session
echo "Creating orchestrations -> session relationship..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "pg_create_object_relationship",
    "args": {
      "source": "default",
      "table": {
        "schema": "public",
        "name": "orchestrations"
      },
      "name": "session",
      "using": {
        "foreign_key_constraint_on": "session_id"
      }
    }
  }' 2>/dev/null | jq '.message // .'

# 3. Create relationship: orchestrations -> tasks (array)
echo "Creating orchestrations -> tasks array relationship..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "pg_create_array_relationship",
    "args": {
      "source": "default",
      "table": {
        "schema": "public",
        "name": "orchestrations"
      },
      "name": "tasks",
      "using": {
        "foreign_key_constraint_on": {
          "column": "orchestration_id",
          "table": {
            "schema": "public",
            "name": "tasks"
          }
        }
      }
    }
  }' 2>/dev/null | jq '.message // .'

# 4. Create relationship: sessions -> orchestrations (array)
echo "Creating sessions -> orchestrations array relationship..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "pg_create_array_relationship",
    "args": {
      "source": "default",
      "table": {
        "schema": "public",
        "name": "sessions"
      },
      "name": "orchestrations",
      "using": {
        "foreign_key_constraint_on": {
          "column": "session_id",
          "table": {
            "schema": "public",
            "name": "orchestrations"
          }
        }
      }
    }
  }' 2>/dev/null | jq '.message // .'

echo ""
echo "✅ Testing the relationships with a nested query..."

# Test query to verify relationships work
curl -X POST http://localhost:8085/v1/graphql \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query TestRelationships { orchestrations(limit: 1, order_by: {started_at: desc}) { orchestration_id status session { session_id } tasks(limit: 3) { task_id name status } } }"
  }' 2>/dev/null | jq '.data.orchestrations[0] // .errors // .'

echo ""
echo "🎉 Done! Testing subscription query that frontend uses..."

# Test the exact query the frontend uses
curl -X POST http://localhost:8085/v1/graphql \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query TestFrontendQuery { sessions(limit: 1, order_by: {created_at: desc}) { id session_id orchestrations { orchestration_id tasks { task_id name status assigned_agent } } } }"
  }' 2>/dev/null | jq '.data.sessions[0] // .errors // .'