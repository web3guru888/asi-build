# GitLab MCP Integration Guide for ASI:BUILD
**Using Zereight's Enhanced GitLab MCP Server v2.0.3**

## 🚀 Quick Start

The ASI:BUILD framework uses **Zereight's GitLab MCP server** (`iwakitakuma/gitlab-mcp`) which provides 83+ tools for comprehensive GitLab automation.

### Why Zereight's Server?

| Feature | Zereight's Server | Previous Server |
|---------|------------------|-----------------|
| **Total Tools** | 83 tools ✅ | 62 tools |
| **get_project** | ✅ Available | ❌ Missing |
| **list_commits** | ✅ Available | ❌ Missing |
| **push_files** | ✅ Available | ❌ Missing |
| **create_branch** | ✅ Available | ❌ Missing |
| **Wiki Support** | ✅ Full support | ❌ None |
| **Pipeline Support** | ✅ Full support | Limited |
| **Docker Image** | `iwakitakuma/gitlab-mcp` | (deprecated) |

## 📦 Installation

### Prerequisites

```bash
# Check Docker is installed
docker --version

# Pull Zereight's MCP server image
docker pull iwakitakuma/gitlab-mcp:latest

# Verify image
docker images | grep gitlab-mcp
# Should show: iwakitakuma/gitlab-mcp (194MB)
```

### Set Your GitLab Token

```bash
# Option 1: Export as environment variable
export GITLAB_TOKEN="your-gitlab-personal-access-token"

# Option 2: Update default in scripts
# Edit integrations/mcp_bridge.py line 23
```

## 🎯 Using MCP Tools

### Method 1: Python Bridge (Recommended)

```python
from integrations.mcp_bridge import MCPBridge
import json

# Initialize bridge (uses Zereight's server)
bridge = MCPBridge()

# Example 1: Get project info (NEW - works directly!)
project = bridge.get_project("asi-build/asi-build")
if "content" in project:
    data = json.loads(project["content"][0]["text"])
    print(f"Last push: {data['last_activity_at']}")

# Example 2: List commits (NEW - previously unavailable!)
commits = bridge.list_commits("asi-build/asi-build", limit=5)

# Example 3: Push multiple files (NEW!)
files = [
    {"path": "README.md", "content": "# Updated"},
    {"path": "docs/guide.md", "content": "New guide"}
]
bridge.push_files("asi-build/asi-build", files, "Update docs")

# Example 4: Create branch (NEW!)
bridge.create_branch("asi-build/asi-build", "feature-x", "main")

# Clean up
bridge._cleanup()
```

### Method 2: Shell Commands

```bash
# Get project details (includes last activity!)
./integrations/mcp_tool.sh get-project '{"project_id":"asi-build/asi-build"}'

# List commits (NEW!)
./integrations/mcp_tool.sh list-commits '{"project_id":"asi-build/asi-build","per_page":10}'

# Create issue
./integrations/mcp_tool.sh create-issue '{
  "project_id": "asi-build/asi-build",
  "title": "New Feature Request",
  "description": "Implement XYZ"
}'

# Update file
./integrations/mcp_tool.sh update-file '{
  "project_id": "asi-build/asi-build",
  "file_path": "README.md",
  "content": "Updated content",
  "commit_message": "Update README",
  "branch": "main"
}'

# See all 83 available tools
./integrations/mcp_tool.sh list-tools
```

### Method 3: Direct Docker

```bash
# Create request file
cat > request.jsonl << EOF
{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true}},"clientInfo":{"name":"test","version":"1.0"}},"id":1}
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_project","arguments":{"project_id":"asi-build/asi-build"}},"id":2}
EOF

# Execute
cat request.jsonl | docker run -i --rm \
  -e GITLAB_PERSONAL_ACCESS_TOKEN="$GITLAB_TOKEN" \
  -e GITLAB_API_URL="https://gitlab.com/api/v4" \
  -e USE_GITLAB_WIKI="true" \
  -e USE_MILESTONE="true" \
  -e USE_PIPELINE="true" \
  iwakitakuma/gitlab-mcp
```

## 📋 Common Operations

### Getting Last Git Push (Now Easy!)

```python
from integrations.mcp_bridge import MCPBridge

bridge = MCPBridge()

# Direct method - no workarounds needed!
last_push = bridge.get_last_push("asi-build/asi-build")
print(last_push)  # "Last push: 2025-08-20 17:08:50 UTC (2 hours ago)"
```

### Working with Commits

```python
# List commits
commits = bridge.list_commits("asi-build/asi-build", limit=10)

# Get specific commit
commit = bridge.get_commit("asi-build/asi-build", "sha123abc")

# Get commit diff
diff = bridge.call_mcp_tool("get_commit_diff", {
    "project_id": "asi-build/asi-build",
    "sha": "sha123abc"
})
```

### Advanced File Operations

```python
# Push multiple files in one commit
files = [
    {
        "path": "src/main.py",
        "content": "print('Hello')"
    },
    {
        "path": "tests/test_main.py",
        "content": "def test_main(): pass"
    }
]

result = bridge.push_files(
    project_id="asi-build/asi-build",
    files=files,
    commit_message="Add main and tests",
    branch="feature-branch"
)

# Create or update single file
bridge.create_or_update_file(
    project_id="asi-build/asi-build",
    file_path="config.yaml",
    content="setting: value",
    commit_message="Update config",
    branch="main"
)
```

### Wiki Operations (NEW!)

```python
# List wiki pages
pages = bridge.list_wiki_pages("asi-build/asi-build")

# Get wiki page
page = bridge.get_wiki_page("asi-build/asi-build", "home")

# Create wiki page
bridge.create_wiki_page(
    project_id="asi-build/asi-build",
    title="API Documentation",
    content="# API Docs\n\nContent here..."
)
```

### Pipeline Management (ENHANCED!)

```python
# List pipelines
pipelines = bridge.list_pipelines("asi-build/asi-build", status="running")

# Create pipeline
pipeline = bridge.create_pipeline("asi-build/asi-build", "main")

# Get pipeline details
details = bridge.get_pipeline("asi-build/asi-build", pipeline_id=123)
```

## 🛠️ All 83 Available Tools

### Project & Repository (15 tools)
- `get_project` ✅ - Get project details with last activity
- `list_projects` - List accessible projects
- `search_repositories` - Search for repositories
- `create_repository` - Create new project
- `fork_repository` - Fork a project
- `get_repository_tree` - List files/directories
- `get_file_contents` - Get file content
- `create_or_update_file` ✅ - Create/update single file
- `push_files` ✅ - Push multiple files
- `create_branch` ✅ - Create new branch
- `list_commits` ✅ - List commits
- `get_commit` ✅ - Get commit details
- `get_commit_diff` ✅ - Get commit changes
- `get_branch_diffs` - Compare branches
- `upload_markdown` - Upload file for markdown

### Issues (10 tools)
- `create_issue` - Create issue
- `get_issue` - Get issue details
- `list_issues` - List issues
- `my_issues` - List assigned issues
- `update_issue` - Update issue
- `delete_issue` - Delete issue
- `list_issue_links` - List linked issues
- `create_issue_link` - Link issues
- `delete_issue_link` - Unlink issues
- `list_issue_discussions` - List issue discussions

### Merge Requests (15 tools)
- `create_merge_request` - Create MR
- `get_merge_request` - Get MR details
- `list_merge_requests` - List MRs
- `update_merge_request` - Update MR
- `merge_merge_request` ✅ - Merge an MR
- `get_merge_request_diffs` - Get MR changes
- `list_merge_request_diffs` - List MR diffs with pagination
- `create_merge_request_thread` - Create MR thread
- `mr_discussions` - List MR discussions
- `create_merge_request_note` - Add MR note
- `update_merge_request_note` - Update MR note
- `list_draft_notes` - List draft notes
- `create_draft_note` - Create draft note
- `publish_draft_note` - Publish draft
- `bulk_publish_draft_notes` - Publish all drafts

### Wiki (5 tools) - NEW!
- `list_wiki_pages` - List wiki pages
- `get_wiki_page` - Get wiki content
- `create_wiki_page` - Create wiki page
- `update_wiki_page` - Update wiki page
- `delete_wiki_page` - Delete wiki page

### Pipelines (9 tools) - ENHANCED!
- `list_pipelines` - List pipelines
- `get_pipeline` - Get pipeline details
- `list_pipeline_jobs` - List pipeline jobs
- `list_pipeline_trigger_jobs` - List trigger jobs
- `get_pipeline_job` - Get job details
- `get_pipeline_job_output` - Get job output
- `create_pipeline` - Create pipeline
- `retry_pipeline` - Retry pipeline
- `cancel_pipeline` - Cancel pipeline

### Milestones (8 tools) - NEW!
- `list_milestones` - List milestones
- `get_milestone` - Get milestone
- `create_milestone` - Create milestone
- `edit_milestone` - Edit milestone
- `delete_milestone` - Delete milestone
- `get_milestone_issue` - Get milestone issues
- `get_milestone_merge_requests` - Get milestone MRs
- `promote_milestone` - Promote milestone

### Users & Groups (7 tools)
- `get_users` - Get user details
- `list_namespaces` - List namespaces
- `get_namespace` - Get namespace details
- `verify_namespace` - Verify namespace exists
- `list_project_members` - List project members
- `list_group_projects` - List group projects
- `list_group_iterations` - List iterations

### Labels & Notes (9 tools)
- `list_labels` - List labels
- `get_label` - Get label
- `create_label` - Create label
- `update_label` - Update label
- `delete_label` - Delete label
- `create_note` - Create note
- `create_issue_note` - Add issue note
- `update_issue_note` - Update issue note
- `download_attachment` - Download attachment

## 🔧 Configuration

### Environment Variables

```bash
# Required
GITLAB_PERSONAL_ACCESS_TOKEN="your-token"

# Optional
GITLAB_API_URL="https://gitlab.com/api/v4"  # For self-hosted
GITLAB_PROJECT_ID="default-project-id"       # Default project
GITLAB_READ_ONLY_MODE="false"                # Restrict to read-only
USE_GITLAB_WIKI="true"                       # Enable wiki tools
USE_MILESTONE="true"                         # Enable milestone tools
USE_PIPELINE="true"                          # Enable pipeline tools
```

### Token Permissions

Minimum required GitLab token scopes:
- `api` - Full API access (recommended)

Or selective scopes:
- `read_api` - Read access
- `read_repository` - Repository read
- `write_repository` - Repository write
- `read_user` - User information

## 🐛 Troubleshooting

### Common Issues

#### Docker Not Running
```bash
# Start Docker
sudo systemctl start docker  # Linux
open -a Docker  # macOS

# Verify
docker ps
```

#### Wrong MCP Server Image
```bash
# Check you have the right image
docker images | grep gitlab-mcp
# Should show: iwakitakuma/gitlab-mcp (194MB)

# If you see the old one, remove it
docker rmi registry.gitlab.com/fforster/gitlab-mcp:latest

# Pull the correct one
docker pull iwakitakuma/gitlab-mcp:latest
```

#### Tool Not Found Error
```python
# If you get "tool 'get_project' not found"
# You're using the old server! Update to Zereight's:

# Check which server initialized
# Should see: "better-gitlab-mcp-server v2.0.3"
```

#### Authentication Issues
```bash
# Test your token
curl -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  https://gitlab.com/api/v4/user

# Should return your user info
```

## 📊 Server Comparison

### What Changed from Previous Server

**Added Tools (21 new):**
- `get_project` - Finally available!
- `list_commits`, `get_commit`, `get_commit_diff`
- `push_files`, `create_or_update_file`
- `create_branch`, `merge_merge_request`
- All wiki tools (5)
- All milestone tools (8)
- Enhanced pipeline tools

**Improved Features:**
- Better error handling
- Proper parameter validation
- Wiki and milestone support
- More reliable connections
- Better documentation

## 🚀 Advanced Usage

### Batch Operations

```python
from integrations.mcp_bridge import MCPBridge
import asyncio

bridge = MCPBridge()

# Get multiple data points efficiently
project = bridge.get_project("asi-build/asi-build")
commits = bridge.list_commits("asi-build/asi-build", limit=5)
issues = bridge.list_issues("asi-build/asi-build")
mrs = bridge.list_merge_requests("asi-build/asi-build")

# Process results...
```

### Custom Tool Calls

```python
# Call any of the 83 tools directly
result = bridge.call_mcp_tool("tool_name", {
    "param1": "value1",
    "param2": "value2"
})
```

## 📚 Resources

- **Docker Image**: `iwakitakuma/gitlab-mcp:latest`
- **Server Version**: 2.0.3 (better-gitlab-mcp-server)
- **Total Tools**: 83
- **Source**: https://github.com/zereight/gitlab-mcp

## 🎉 Migration Complete

ASI:BUILD has successfully migrated from the previous GitLab MCP server (62 tools) to Zereight's enhanced server (83 tools). Key improvements include:

1. ✅ Direct `get_project` support (no workarounds!)
2. ✅ Full commit history access
3. ✅ Multi-file push capabilities
4. ✅ Wiki and milestone management
5. ✅ Enhanced pipeline control

---

*Last Updated: 2025-08-20*
*ASI:BUILD Framework - GitLab MCP Integration v2.0*