#!/bin/bash
#
# MCP Tool Wrapper - Call GitLab MCP tools from shell
# Using Zereight's enhanced GitLab MCP server (83+ tools)
# Usage: ./mcp_tool.sh <tool_name> [arguments_json]
#

GITLAB_TOKEN="${GITLAB_TOKEN:?GITLAB_TOKEN environment variable must be set}"

# Function to call MCP tool
call_mcp_tool() {
    local tool_name=$1
    local arguments=${2:-"{}"}
    
    # Create MCP protocol messages with proper initialization
    cat > /tmp/mcp_request.jsonl << EOF
{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true},"sampling":{}},"clientInfo":{"name":"mcp-shell","version":"1.0.0"}},"id":1}
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"$tool_name","arguments":$arguments},"id":2}
EOF
    
    # Execute via Docker using zereight's server
    cat /tmp/mcp_request.jsonl | docker run -i --rm \
        -e GITLAB_PERSONAL_ACCESS_TOKEN="$GITLAB_TOKEN" \
        -e GITLAB_API_URL="https://gitlab.com/api/v4" \
        -e GITLAB_READ_ONLY_MODE="false" \
        -e USE_GITLAB_WIKI="true" \
        -e USE_MILESTONE="true" \
        -e USE_PIPELINE="true" \
        iwakitakuma/gitlab-mcp 2>/dev/null \
    | grep '"id":2' \
    | jq -r '.result'
    
    # Clean up
    rm -f /tmp/mcp_request.jsonl
}

# Main script
case "$1" in
    # Project operations
    get-project)
        # Usage: ./mcp_tool.sh get-project '{"project_id":"asi-build/asi-build"}'
        call_mcp_tool "get_project" "$2"
        ;;
    
    list-projects)
        # Usage: ./mcp_tool.sh list-projects '{"per_page":10}'
        call_mcp_tool "list_projects" "${2:-{}}"
        ;;
    
    search-repos)
        # Usage: ./mcp_tool.sh search-repos '{"search":"ASI"}'
        call_mcp_tool "search_repositories" "$2"
        ;;
    
    # Issue operations
    create-issue)
        # Usage: ./mcp_tool.sh create-issue '{"project_id":"123","title":"Test Issue"}'
        call_mcp_tool "create_issue" "$2"
        ;;
    
    list-issues)
        # Usage: ./mcp_tool.sh list-issues '{"project_id":"123","state":"opened"}'
        call_mcp_tool "list_issues" "${2:-{}}"
        ;;
    
    get-issue)
        # Usage: ./mcp_tool.sh get-issue '{"project_id":"123","issue_iid":1}'
        call_mcp_tool "get_issue" "$2"
        ;;
    
    # MR operations
    create-mr)
        # Usage: ./mcp_tool.sh create-mr '{"project_id":"123","source_branch":"feature","target_branch":"main","title":"New MR"}'
        call_mcp_tool "create_merge_request" "$2"
        ;;
    
    list-mrs)
        # Usage: ./mcp_tool.sh list-mrs '{"project_id":"123"}'
        call_mcp_tool "list_merge_requests" "$2"
        ;;
    
    merge-mr)
        # Usage: ./mcp_tool.sh merge-mr '{"project_id":"123","merge_request_iid":1}'
        call_mcp_tool "merge_merge_request" "$2"
        ;;
    
    # Repository operations
    get-file)
        # Usage: ./mcp_tool.sh get-file '{"project_id":"123","file_path":"README.md"}'
        call_mcp_tool "get_file_contents" "$2"
        ;;
    
    update-file)
        # Usage: ./mcp_tool.sh update-file '{"project_id":"123","file_path":"README.md","content":"..","commit_message":"Update"}'
        call_mcp_tool "create_or_update_file" "$2"
        ;;
    
    push-files)
        # Usage: ./mcp_tool.sh push-files '{"project_id":"123","files":[...],"commit_message":"Multi-file update"}'
        call_mcp_tool "push_files" "$2"
        ;;
    
    create-branch)
        # Usage: ./mcp_tool.sh create-branch '{"project_id":"123","branch":"feature-x","ref":"main"}'
        call_mcp_tool "create_branch" "$2"
        ;;
    
    # Commit operations
    list-commits)
        # Usage: ./mcp_tool.sh list-commits '{"project_id":"123","per_page":10}'
        call_mcp_tool "list_commits" "$2"
        ;;
    
    get-commit)
        # Usage: ./mcp_tool.sh get-commit '{"project_id":"123","sha":"abc123"}'
        call_mcp_tool "get_commit" "$2"
        ;;
    
    # Pipeline operations
    list-pipelines)
        # Usage: ./mcp_tool.sh list-pipelines '{"project_id":"123"}'
        call_mcp_tool "list_pipelines" "$2"
        ;;
    
    get-pipeline)
        # Usage: ./mcp_tool.sh get-pipeline '{"project_id":"123","pipeline_id":456}'
        call_mcp_tool "get_pipeline" "$2"
        ;;
    
    # Wiki operations
    list-wiki)
        # Usage: ./mcp_tool.sh list-wiki '{"project_id":"123"}'
        call_mcp_tool "list_wiki_pages" "$2"
        ;;
    
    get-wiki)
        # Usage: ./mcp_tool.sh get-wiki '{"project_id":"123","slug":"home"}'
        call_mcp_tool "get_wiki_page" "$2"
        ;;
    
    # List all tools
    list-tools)
        cat > /tmp/mcp_request.jsonl << EOF
{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true}},"clientInfo":{"name":"mcp-shell","version":"1.0.0"}},"id":1}
{"jsonrpc":"2.0","method":"tools/list","id":2}
EOF
        cat /tmp/mcp_request.jsonl | docker run -i --rm \
            -e GITLAB_PERSONAL_ACCESS_TOKEN="$GITLAB_TOKEN" \
            iwakitakuma/gitlab-mcp 2>/dev/null \
        | grep '"id":2' \
        | jq '.result.tools[].name' \
        | sort
        rm -f /tmp/mcp_request.jsonl
        ;;
    
    # Help
    help|--help|-h)
        echo "GitLab MCP Tool Wrapper (Zereight's Enhanced Server)"
        echo "83+ tools available for GitLab operations"
        echo ""
        echo "Usage: $0 <command> [arguments_json]"
        echo ""
        echo "Project Commands:"
        echo "  get-project <json>      - Get project details (includes last activity!)"
        echo "  list-projects <json>    - List accessible projects"
        echo "  search-repos <json>     - Search repositories"
        echo ""
        echo "Issue Commands:"
        echo "  create-issue <json>     - Create new issue"
        echo "  list-issues <json>      - List issues"
        echo "  get-issue <json>        - Get specific issue"
        echo ""
        echo "Merge Request Commands:"
        echo "  create-mr <json>        - Create merge request"
        echo "  list-mrs <json>         - List merge requests"
        echo "  merge-mr <json>         - Merge a merge request"
        echo ""
        echo "Repository Commands:"
        echo "  get-file <json>         - Get file contents"
        echo "  update-file <json>      - Create/update file"
        echo "  push-files <json>       - Push multiple files"
        echo "  create-branch <json>    - Create new branch"
        echo ""
        echo "Commit Commands:"
        echo "  list-commits <json>     - List commits"
        echo "  get-commit <json>       - Get commit details"
        echo ""
        echo "Pipeline Commands:"
        echo "  list-pipelines <json>   - List pipelines"
        echo "  get-pipeline <json>     - Get pipeline details"
        echo ""
        echo "Wiki Commands:"
        echo "  list-wiki <json>        - List wiki pages"
        echo "  get-wiki <json>         - Get wiki page"
        echo ""
        echo "Other Commands:"
        echo "  list-tools              - List all 83+ available tools"
        echo ""
        echo "Example:"
        echo "  $0 get-project '{\"project_id\":\"asi-build/asi-build\"}'"
        ;;
    
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac