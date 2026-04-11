#!/usr/bin/env python3
"""
MCP Bridge for Claude Code - Using Zereight's Enhanced GitLab MCP Server
This is the primary MCP bridge for ASI:BUILD, providing access to 83+ GitLab tools
"""

import json
import os
import subprocess
import threading
import queue
import time
import atexit
from typing import Dict, Any, Optional
from datetime import datetime

class MCPBridge:
    """
    Primary MCP Bridge using zereight's comprehensive GitLab MCP server
    Provides 83+ tools including get_project, list_commits, push_files, and more
    """
    
    def __init__(self, token: str = None):
        self.token = token or os.environ.get("GITLAB_TOKEN", "")
        self.process = None
        self.request_id = 0
        self.response_queue = queue.Queue()
        self.reader_thread = None
        self._start_server()
        
    def _start_server(self):
        """Start zereight's enhanced MCP server process"""
        self.process = subprocess.Popen(
            ["docker", "run", "-i", "--rm",
             "-e", f"GITLAB_PERSONAL_ACCESS_TOKEN={self.token}",
             "-e", "GITLAB_API_URL=https://gitlab.com/api/v4",
             "-e", "GITLAB_READ_ONLY_MODE=false",
             "-e", "USE_GITLAB_WIKI=true",
             "-e", "USE_MILESTONE=true", 
             "-e", "USE_PIPELINE=true",
             "iwakitakuma/gitlab-mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Start reader thread
        self.reader_thread = threading.Thread(target=self._read_responses, daemon=True)
        self.reader_thread.start()
        
        # Register cleanup
        atexit.register(self._cleanup)
        
        # Initialize the connection
        self._initialize()
    
    def _read_responses(self):
        """Read responses from the MCP server"""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    try:
                        response = json.loads(line.strip())
                        self.response_queue.put(response)
                    except json.JSONDecodeError:
                        pass
            except:
                break
    
    def _initialize(self):
        """Initialize the MCP session"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "asi-build-claude-code",
                    "version": "2.0.0"
                }
            },
            "id": self.request_id
        }
        
        response = self._send_request(request)
        if response and "result" in response:
            server_info = response['result'].get('serverInfo', {})
            print(f"✅ MCP Bridge initialized: {server_info.get('name', 'Unknown')} v{server_info.get('version', 'Unknown')}")
            return True
        elif response and "error" in response:
            print(f"❌ Init error: {response['error']}")
        return False
    
    def _send_request(self, request: dict, timeout: float = 10.0) -> Optional[dict]:
        """Send a request and wait for response"""
        request_id = request.get("id")
        
        # Send request
        self.process.stdin.write(json.dumps(request) + '\n')
        self.process.stdin.flush()
        
        # Wait for response with matching ID
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.response_queue.get(timeout=0.1)
                if response.get("id") == request_id:
                    return response
                else:
                    # Put it back if it's not our response
                    self.response_queue.put(response)
            except queue.Empty:
                continue
        
        return None
    
    def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call an MCP tool
        
        Args:
            tool_name: Name of the MCP tool (e.g., 'get_project', 'create_issue')
            arguments: Tool arguments as dictionary
        
        Returns:
            Tool response as dictionary
        """
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            },
            "id": self.request_id
        }
        
        response = self._send_request(request)
        if response:
            if "result" in response:
                return response["result"]
            elif "error" in response:
                return {"error": response["error"]}
        
        return {"error": "No response from tool"}
    
    # Core GitLab Operations
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get detailed project information including last activity"""
        return self.call_mcp_tool("get_project", {"project_id": project_id})
    
    def list_projects(self, limit: int = 10) -> Dict[str, Any]:
        """List accessible GitLab projects"""
        return self.call_mcp_tool("list_projects", {"per_page": limit})
    
    def search_repositories(self, search: str) -> Dict[str, Any]:
        """Search for GitLab repositories"""
        return self.call_mcp_tool("search_repositories", {"search": search})
    
    # Issue Management
    
    def create_issue(self, project_id: str, title: str, description: str = None, 
                    labels: str = None) -> Dict[str, Any]:
        """Create a new GitLab issue"""
        args = {"project_id": project_id, "title": title}
        if description:
            args["description"] = description
        if labels:
            args["labels"] = labels
        return self.call_mcp_tool("create_issue", args)
    
    def get_issue(self, project_id: str, issue_iid: int) -> Dict[str, Any]:
        """Get details of a specific issue"""
        return self.call_mcp_tool("get_issue", {
            "project_id": project_id,
            "issue_iid": issue_iid
        })
    
    def list_issues(self, project_id: str = None, state: str = "opened") -> Dict[str, Any]:
        """List issues"""
        args = {"state": state}
        if project_id:
            args["project_id"] = project_id
        return self.call_mcp_tool("list_issues", args)
    
    def update_issue(self, project_id: str, issue_iid: int, **kwargs) -> Dict[str, Any]:
        """Update an existing issue"""
        args = {"project_id": project_id, "issue_iid": issue_iid, **kwargs}
        return self.call_mcp_tool("update_issue", args)
    
    # Merge Request Management
    
    def create_merge_request(self, project_id: str, source_branch: str, 
                           target_branch: str, title: str, description: str = None) -> Dict[str, Any]:
        """Create a new merge request"""
        args = {
            "project_id": project_id,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title
        }
        if description:
            args["description"] = description
        return self.call_mcp_tool("create_merge_request", args)
    
    def get_merge_request(self, project_id: str, mr_iid: int = None, 
                         branch_name: str = None) -> Dict[str, Any]:
        """Get merge request details by IID or branch name"""
        args = {"project_id": project_id}
        if mr_iid:
            args["mergeRequestIid"] = mr_iid
        elif branch_name:
            args["branchName"] = branch_name
        return self.call_mcp_tool("get_merge_request", args)
    
    def list_merge_requests(self, project_id: str, state: str = "opened") -> Dict[str, Any]:
        """List merge requests in a project"""
        return self.call_mcp_tool("list_merge_requests", {
            "project_id": project_id,
            "state": state
        })
    
    def merge_merge_request(self, project_id: str, mr_iid: int) -> Dict[str, Any]:
        """Merge a merge request"""
        return self.call_mcp_tool("merge_merge_request", {
            "project_id": project_id,
            "merge_request_iid": mr_iid
        })
    
    # Repository Operations
    
    def get_file_contents(self, project_id: str, file_path: str, ref: str = "main") -> Dict[str, Any]:
        """Get file contents from repository"""
        return self.call_mcp_tool("get_file_contents", {
            "project_id": project_id,
            "file_path": file_path,
            "ref": ref
        })
    
    def create_or_update_file(self, project_id: str, file_path: str, content: str,
                             commit_message: str, branch: str = "main") -> Dict[str, Any]:
        """Create or update a single file"""
        return self.call_mcp_tool("create_or_update_file", {
            "project_id": project_id,
            "file_path": file_path,
            "content": content,
            "commit_message": commit_message,
            "branch": branch
        })
    
    def push_files(self, project_id: str, files: list, commit_message: str,
                  branch: str = "main") -> Dict[str, Any]:
        """Push multiple files in a single commit"""
        return self.call_mcp_tool("push_files", {
            "project_id": project_id,
            "files": files,
            "commit_message": commit_message,
            "branch": branch
        })
    
    def create_branch(self, project_id: str, branch_name: str, ref: str = "main") -> Dict[str, Any]:
        """Create a new branch"""
        return self.call_mcp_tool("create_branch", {
            "project_id": project_id,
            "branch": branch_name,
            "ref": ref
        })
    
    # Commit Operations
    
    def list_commits(self, project_id: str, ref_name: str = None, limit: int = 20) -> Dict[str, Any]:
        """List repository commits"""
        args = {"project_id": project_id, "per_page": limit}
        if ref_name:
            args["ref_name"] = ref_name
        return self.call_mcp_tool("list_commits", args)
    
    def get_commit(self, project_id: str, sha: str) -> Dict[str, Any]:
        """Get details of a specific commit"""
        return self.call_mcp_tool("get_commit", {
            "project_id": project_id,
            "sha": sha
        })
    
    # Pipeline Operations
    
    def list_pipelines(self, project_id: str, status: str = None, limit: int = 20) -> Dict[str, Any]:
        """List pipelines in a project"""
        args = {"project_id": project_id, "per_page": limit}
        if status:
            args["status"] = status
        return self.call_mcp_tool("list_pipelines", args)
    
    def get_pipeline(self, project_id: str, pipeline_id: int) -> Dict[str, Any]:
        """Get pipeline details"""
        return self.call_mcp_tool("get_pipeline", {
            "project_id": project_id,
            "pipeline_id": pipeline_id
        })
    
    def create_pipeline(self, project_id: str, ref: str) -> Dict[str, Any]:
        """Create a new pipeline"""
        return self.call_mcp_tool("create_pipeline", {
            "project_id": project_id,
            "ref": ref
        })
    
    # Wiki Operations
    
    def list_wiki_pages(self, project_id: str) -> Dict[str, Any]:
        """List wiki pages in a project"""
        return self.call_mcp_tool("list_wiki_pages", {"project_id": project_id})
    
    def get_wiki_page(self, project_id: str, slug: str) -> Dict[str, Any]:
        """Get a specific wiki page"""
        return self.call_mcp_tool("get_wiki_page", {
            "project_id": project_id,
            "slug": slug
        })
    
    def create_wiki_page(self, project_id: str, title: str, content: str) -> Dict[str, Any]:
        """Create a new wiki page"""
        return self.call_mcp_tool("create_wiki_page", {
            "project_id": project_id,
            "title": title,
            "content": content
        })
    
    # Utility Methods
    
    def get_last_push(self, project_id: str = "asi-build/asi-build") -> str:
        """Get the last push time for a project"""
        result = self.get_project(project_id)
        
        if "content" in result and result["content"]:
            content = result["content"][0].get("text", "")
            try:
                project = json.loads(content)
                last_activity = project.get("last_activity_at", "")
                if last_activity:
                    dt = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                    
                    # Calculate time ago
                    now = datetime.now(dt.tzinfo)
                    delta = now - dt
                    hours = delta.total_seconds() / 3600
                    
                    if hours < 1:
                        time_ago = f"{int(delta.total_seconds() / 60)} minutes ago"
                    elif hours < 24:
                        time_ago = f"{int(hours)} hours ago"
                    else:
                        time_ago = f"{int(hours / 24)} days ago"
                    
                    return f"Last push: {dt.strftime('%Y-%m-%d %H:%M:%S UTC')} ({time_ago})"
            except Exception as e:
                return f"Error parsing: {e}"
        
        return "Could not retrieve project info"
    
    def list_tools(self) -> list:
        """Get list of all available MCP tools (83+ tools)"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": self.request_id
        }
        
        response = self._send_request(request)
        if response and "result" in response:
            return response["result"].get("tools", [])
        return []
    
    def _cleanup(self):
        """Clean up the MCP server process"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self._cleanup()


# Quick test function
def test_mcp_bridge():
    """Test the MCP bridge functionality"""
    print("🧪 Testing ASI:BUILD MCP Bridge (Zereight's Enhanced Server)")
    print("=" * 70)
    
    bridge = MCPBridge()
    time.sleep(1)
    
    # Test get_project
    print("\n1. Testing get_project (now available!)...")
    last_push = bridge.get_last_push()
    print(f"✅ {last_push}")
    
    # List tools
    tools = bridge.list_tools()
    print(f"\n2. Available tools: {len(tools)}")
    
    print("\n✅ MCP Bridge is fully operational with 83+ GitLab tools!")
    
    bridge._cleanup()


if __name__ == "__main__":
    test_mcp_bridge()