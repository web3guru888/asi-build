# GitLab MCP Integration User Guide
**Using Zereight's Enhanced GitLab MCP Server (83+ Tools)**

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Using MCP Tools](#using-mcp-tools)
5. [Common Operations](#common-operations)
6. [Advanced Usage](#advanced-usage)
7. [Troubleshooting](#troubleshooting)
8. [Security](#security)

## Overview

The GitLab MCP (Model Context Protocol) integration enables Claude Code to interact with GitLab through 83+ specialized tools using Zereight's enhanced MCP server. Since Claude Code doesn't have native MCP support, we use Docker-based workarounds to access these tools.

### What You Can Do
- Create and manage issues
- Create and review merge requests
- Commit code changes directly to GitLab
- Manage CI/CD pipelines
- Handle discussions and todos
- Access repository files
- And much more!

## Prerequisites

### Required
- Docker installed and running
- GitLab Personal Access Token (PAT)
- ASI:BUILD repository cloned locally

### Check Prerequisites
```bash
# Check Docker
docker --version
docker ps

# Check MCP image
docker images | grep gitlab-mcp

# If image is missing, pull it:
docker pull iwakitakuma/gitlab-mcp:latest
```

## Quick Start

### 1. Set Your GitLab Token

```bash
# Option 1: Export as environment variable
export GITLAB_TOKEN="your-gitlab-token-here"

# Option 2: The scripts use a default token if none is set
# (Update the default in the scripts for permanent use)
```

### 2. Test the Connection

```bash
# Quick test
./test_mcp_stdio.sh

# Or use the demo script
python3 integrations/demo_mcp_usage.py
```

## Using MCP Tools

### Method 1: Shell Commands (Easiest)

```bash
# Get current user info
./integrations/mcp_tool.sh get-user

# List projects
./integrations/mcp_tool.sh list-projects

# Create an issue
./integrations/mcp_tool.sh create-issue '{
  "project_id": "asi-build/asi-build",
  "title": "New Feature Request",
  "description": "Implement XYZ functionality"
}'

# List issues
./integrations/mcp_tool.sh list-issues '{"project_id": "asi-build/asi-build"}'

# Get help
./integrations/mcp_tool.sh help
```

### Method 2: Python Script (More Flexible)

```python
from integrations.mcp_bridge import MCPBridge
import asyncio

async def main():
    # Initialize bridge
    bridge = MCPBridge(token="your-token-here")  # Optional, uses default if not provided
    
    # Get current user
    user = await bridge.get_current_user()
    print(f"Logged in as: {user}")
    
    # Create an issue
    issue = await bridge.create_issue(
        project_id="asi-build/asi-build",
        title="Bug Report",
        description="Found an issue with..."
    )
    print(f"Created issue: {issue}")
    
    # List merge requests
    mrs = await bridge.list_merge_requests(
        project_id="asi-build/asi-build",
        state="opened"
    )
    print(f"Open MRs: {mrs}")

# Run
asyncio.run(main())
```

### Method 3: Direct Docker (Advanced)

```bash
# Create a request file
cat > request.json << EOF
{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05"},"id":1}
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_user"},"id":2}
EOF

# Send to MCP server
cat request.json | docker run -i --rm \
  -e GITLAB_TOKEN="$GITLAB_TOKEN" \
  iwakitakuma/gitlab-mcp:latest
```

## Common Operations

### Issues Management

```bash
# Create issue
./integrations/mcp_tool.sh create-issue '{
  "project_id": "asi-build/asi-build",
  "title": "Issue Title",
  "description": "Issue description",
  "labels": "bug,priority"
}'

# Get specific issue
./integrations/mcp_tool.sh get-issue '{
  "project_id": "asi-build/asi-build",
  "issue_iid": 1
}'

# List all issues
./integrations/mcp_tool.sh list-issues '{
  "project_id": "asi-build/asi-build",
  "state": "opened"
}'
```

### Merge Requests

```bash
# Create MR
./integrations/mcp_tool.sh create-mr '{
  "project_id": "asi-build/asi-build",
  "source_branch": "feature-branch",
  "target_branch": "main",
  "title": "Add new feature"
}'

# List MRs
./integrations/mcp_tool.sh list-mrs '{
  "project_id": "asi-build/asi-build"
}'
```

### Repository Operations

```bash
# Get file contents
./integrations/mcp_tool.sh get-file '{
  "project_id": "asi-build/asi-build",
  "file_path": "README.md"
}'

# Create a commit (using Python)
python3 -c "
from integrations.mcp_bridge import MCPBridge
import asyncio

async def commit():
    bridge = MCPBridge()
    result = await bridge.create_commit(
        project_id='asi-build/asi-build',
        branch='main',
        commit_message='Update documentation',
        action='update',
        path='docs/guide.md',
        contents='# Updated content here'
    )
    print(result)

asyncio.run(commit())
"
```

### Todo Management

```bash
# List your todos
./integrations/mcp_tool.sh list-todos

# Complete a todo
./integrations/mcp_tool.sh complete-todo '{"id": 123}'
```

## Advanced Usage

### Custom MCP Tool Calls

```python
from integrations.mcp_bridge import MCPBridge
import asyncio

async def custom_tool_call():
    bridge = MCPBridge()
    
    # Call any of the 70+ available tools
    result = await bridge.call_mcp_tool(
        tool_name="search_projects",
        arguments={
            "search": "ASI",
            "limit": 10
        }
    )
    return result

# Run
result = asyncio.run(custom_tool_call())
print(result)
```

### Batch Operations

```python
import asyncio
from integrations.mcp_bridge import MCPBridge

async def batch_operations():
    bridge = MCPBridge()
    
    # Run multiple operations concurrently
    results = await asyncio.gather(
        bridge.get_current_user(),
        bridge.list_projects(limit=5),
        bridge.list_todos(limit=10),
        bridge.list_merge_requests("asi-build/asi-build")
    )
    
    user, projects, todos, mrs = results
    return {
        "user": user,
        "projects": projects,
        "todos": todos,
        "merge_requests": mrs
    }

# Execute
data = asyncio.run(batch_operations())
```

### Pipeline Management

```python
# List pipeline jobs
async def get_pipeline_info():
    bridge = MCPBridge()
    
    # Get latest pipeline
    pipelines = await bridge.call_mcp_tool(
        "list_pipelines",
        {"project_id": "asi-build/asi-build", "limit": 1}
    )
    
    # Get jobs for that pipeline
    if pipelines:
        pipeline_id = pipelines["content"][0]["id"]
        jobs = await bridge.call_mcp_tool(
            "list_pipeline_jobs",
            {"project_id": "asi-build/asi-build", "pipeline_id": pipeline_id}
        )
        return jobs
```

## Troubleshooting

### Common Issues

#### 1. Docker Not Running
```bash
# Start Docker
sudo systemctl start docker  # Linux
open -a Docker  # macOS

# Verify
docker ps
```

#### 2. Authentication Failed
```bash
# Check token is set
echo $GITLAB_TOKEN

# Test token directly
curl -H "PRIVATE-TOKEN: $GITLAB_TOKEN" https://gitlab.com/api/v4/user
```

#### 3. MCP Server Not Responding
```bash
# Check if container runs
docker run --rm iwakitakuma/gitlab-mcp:latest --help

# Pull latest image
docker pull iwakitakuma/gitlab-mcp:latest
```

#### 4. Permission Denied
```bash
# Make scripts executable
chmod +x integrations/mcp_tool.sh
chmod +x test_mcp_stdio.sh
```

### Debug Mode

```bash
# Enable verbose output
cat > debug_mcp.sh << 'EOF'
#!/bin/bash
set -x  # Enable debug output

echo "Testing MCP connection..."
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}
{"jsonrpc":"2.0","method":"tools/list","id":2}' | \
docker run -i --rm \
  -e GITLAB_TOKEN="$GITLAB_TOKEN" \
  iwakitakuma/gitlab-mcp:latest 2>&1
EOF

chmod +x debug_mcp.sh
./debug_mcp.sh
```

## Security

### Best Practices

1. **Never commit tokens to Git**
   ```bash
   # Add to .gitignore
   echo "*.token" >> .gitignore
   echo ".env" >> .gitignore
   ```

2. **Use environment variables**
   ```bash
   # Create .env file (don't commit!)
   echo "GITLAB_TOKEN=your-token-here" > .env
   
   # Load in scripts
   source .env
   ```

3. **Limit token scope**
   - Create tokens with minimal required permissions
   - Use project-specific tokens when possible
   - Rotate tokens regularly

4. **Secure Docker**
   ```bash
   # Run with limited permissions
   docker run --rm --read-only \
     -e GITLAB_TOKEN="$GITLAB_TOKEN" \
     iwakitakuma/gitlab-mcp:latest
   ```

### Token Permissions Required

Minimum GitLab token scopes needed:
- `api` - Full API access (recommended)
- OR selective scopes:
  - `read_api` - Read access
  - `read_repository` - Repository access
  - `write_repository` - Write to repository
  - `read_user` - User information

## Available MCP Tools

### Complete Tool List

Run this to see all 70+ available tools:
```bash
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}
{"jsonrpc":"2.0","method":"tools/list","id":2}' | \
docker run -i --rm -e GITLAB_TOKEN="$GITLAB_TOKEN" \
  iwakitakuma/gitlab-mcp:latest | \
grep '"id":2' | jq '.result.tools[].name'
```

### Categories

**Issues & Epics**
- create_issue, edit_issue, get_issue
- create_epic, edit_epic, get_epic
- issue_time_tracking

**Merge Requests**
- create_merge_request, edit_merge_request
- get_merge_request, list_project_merge_requests
- get_merge_request_approvals, get_merge_request_commits

**Repository**
- create_commit, get_repository_file_contents
- get_repository_tree, search_repository

**Pipelines & Jobs**
- list_pipelines, get_pipeline, retry_pipeline
- list_pipeline_jobs, get_job, retry_job

**Discussions**
- discussion_new, discussion_list
- discussion_add_note, discussion_resolve

**Users & Projects**
- get_user, get_user_status
- get_project, list_projects, search_projects

**Todos & Snippets**
- list_user_todos, complete_todo_item
- create_snippet, get_snippet, update_snippet

## Integration with ASI:BUILD

The MCP tools follow the Kenny Integration pattern:

```python
from integrations.gitlab_mcp_integration import GitLabMCPIntegration

# Initialize with Kenny Integration
integration = GitLabMCPIntegration()

# Use with Kenny's event system
await integration.kenny_integration.emit("gitlab.issue.create", {
    "project": "asi-build/asi-build",
    "title": "New Issue"
})

# Subscribe to events
integration.kenny_integration.on("gitlab.issue.created", lambda data: 
    print(f"Issue created: {data}")
)
```

## Getting Help

### Resources
- GitLab MCP Repository: https://github.com/zereight/gitlab-mcp
- ASI:BUILD Wiki: https://gitlab.com/asi-build/asi-build/-/wikis/home
- GitLab API Docs: https://docs.gitlab.com/ee/api/

### Quick Reference Card

```bash
# Essential Commands
./integrations/mcp_tool.sh help              # Show all commands
./integrations/mcp_tool.sh get-user          # Test connection
./integrations/mcp_tool.sh list-projects     # List your projects
./integrations/mcp_tool.sh list-todos        # Show your todos

# Python Quick Start
python3 integrations/demo_mcp_usage.py       # Run demo
python3 integrations/mcp_bridge.py           # Test bridge

# Docker Direct
./test_mcp_stdio.sh                          # Test stdio mode
```

## Conclusion

The GitLab MCP integration provides powerful GitLab automation capabilities within the ASI:BUILD framework. While Claude Code doesn't have native MCP support, our Docker-based workarounds provide full access to all MCP tools.

For questions or issues, check the troubleshooting section or create an issue in the ASI:BUILD repository using the MCP tools you just learned!

---

*Last Updated: 2025-08-20*
*Version: 1.0.0*
*Part of ASI:BUILD Framework*