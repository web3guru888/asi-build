#!/bin/bash

# Fix Hasura Relationships for ASI-Code
# This script creates all necessary relationships between tables

HASURA_ENDPOINT="http://localhost:8085/v1/metadata"
HASURA_SECRET="asi_hasura_admin_secret_2024"

echo "🔧 Fixing Hasura relationships..."

# 1. Create relationship: tasks -> orchestration
echo "Creating tasks -> orchestration relationship..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "create_object_relationship",
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
  }' 2>/dev/null

# 2. Create relationship: orchestrations -> session
echo "Creating orchestrations -> session relationship..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "create_object_relationship",
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
  }' 2>/dev/null

# 3. Create relationship: orchestrations -> tasks (array)
echo "Creating orchestrations -> tasks array relationship..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "create_array_relationship",
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
  }' 2>/dev/null

# 4. Create relationship: sessions -> orchestrations (array)
echo "Creating sessions -> orchestrations array relationship..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "create_array_relationship",
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
  }' 2>/dev/null

# 5. Create relationship: sessions -> commands (array)
echo "Creating sessions -> commands array relationship..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "create_array_relationship",
    "args": {
      "source": "default",
      "table": {
        "schema": "public",
        "name": "sessions"
      },
      "name": "commands",
      "using": {
        "foreign_key_constraint_on": {
          "column": "session_id",
          "table": {
            "schema": "public",
            "name": "commands"
          }
        }
      }
    }
  }' 2>/dev/null

# 6. Create relationship: commands -> session
echo "Creating commands -> session relationship..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "create_object_relationship",
    "args": {
      "source": "default",
      "table": {
        "schema": "public",
        "name": "commands"
      },
      "name": "session",
      "using": {
        "foreign_key_constraint_on": "session_id"
      }
    }
  }' 2>/dev/null

# 7. Create relationship: user_messages -> session
echo "Creating user_messages -> session relationship..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "create_object_relationship",
    "args": {
      "source": "default",
      "table": {
        "schema": "public",
        "name": "user_messages"
      },
      "name": "session",
      "using": {
        "foreign_key_constraint_on": "session_id"
      }
    }
  }' 2>/dev/null

# 8. Create relationship: sessions -> user_messages (array)
echo "Creating sessions -> user_messages array relationship..."
curl -X POST $HASURA_ENDPOINT \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "create_array_relationship",
    "args": {
      "source": "default",
      "table": {
        "schema": "public",
        "name": "sessions"
      },
      "name": "user_messages",
      "using": {
        "foreign_key_constraint_on": {
          "column": "session_id",
          "table": {
            "schema": "public",
            "name": "user_messages"
          }
        }
      }
    }
  }' 2>/dev/null

echo ""
echo "✅ Relationships created!"
echo ""
echo "Testing the relationships with a query..."

# Test query to verify relationships work
curl -X POST http://localhost:8085/v1/graphql \
  -H "x-hasura-admin-secret: $HASURA_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query TestRelationships { orchestrations(limit: 1) { orchestration_id session { session_id } tasks { task_id name status } } }"
  }' 2>/dev/null | jq '.'

echo ""
echo "🎉 Hasura relationships fixed!"