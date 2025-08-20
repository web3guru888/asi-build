#!/usr/bin/env python3
"""
GitLab Project Creator for ASI:BUILD
Creates a new GitLab project using the API and pushes the code
"""

import os
import sys
import json
import subprocess
import getpass
try:
    import requests
except ImportError:
    print("Installing requests library...")
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"])
    import requests

def create_gitlab_project():
    """Create a new GitLab project using the API"""
    
    print("=" * 50)
    print("ASI:BUILD GitLab Project Creator")
    print("=" * 50)
    print("\nThis script will create a new GitLab project and push your code.\n")
    
    # Get GitLab token
    print("You need a GitLab Personal Access Token with 'api' scope.")
    print("Create one at: https://gitlab.com/-/profile/personal_access_tokens")
    print("Scopes needed: api, read_repository, write_repository\n")
    
    token = getpass.getpass("Enter your GitLab Personal Access Token: ")
    
    if not token:
        print("Token is required. Exiting.")
        return False
    
    # Project details
    project_name = input("Enter project name (default: asi-build): ").strip() or "asi-build"
    project_path = input(f"Enter project path (default: {project_name}): ").strip() or project_name
    description = input("Enter project description (optional): ").strip() or "ASI:BUILD - Unified Framework for Artificial Superintelligence"
    
    # Visibility
    print("\nProject visibility:")
    print("1. Private (default)")
    print("2. Internal") 
    print("3. Public")
    visibility_choice = input("Choose visibility (1-3): ").strip() or "1"
    
    visibility_map = {
        "1": "private",
        "2": "internal", 
        "3": "public"
    }
    visibility = visibility_map.get(visibility_choice, "private")
    
    # Create project via API
    print(f"\nCreating GitLab project '{project_name}'...")
    
    headers = {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json"
    }
    
    data = {
        "name": project_name,
        "path": project_path,
        "description": description,
        "visibility": visibility,
        "initialize_with_readme": False,
        "issues_enabled": True,
        "merge_requests_enabled": True,
        "wiki_enabled": True,
        "snippets_enabled": True,
        "packages_enabled": True,
        "pages_access_level": "private" if visibility == "private" else "enabled"
    }
    
    # Topics/tags for the project
    data["topics"] = [
        "artificial-intelligence",
        "superintelligence",
        "agi",
        "asi",
        "machine-learning",
        "deep-learning",
        "consciousness",
        "quantum-computing"
    ]
    
    try:
        response = requests.post(
            "https://gitlab.com/api/v4/projects",
            headers=headers,
            json=data
        )
        
        if response.status_code == 201:
            project = response.json()
            print("✅ Project created successfully!")
            print(f"Project ID: {project['id']}")
            print(f"Project URL: {project['web_url']}")
            print(f"Git URL (HTTPS): {project['http_url_to_repo']}")
            print(f"Git URL (SSH): {project['ssh_url_to_repo']}")
            
            return project
        else:
            print(f"❌ Failed to create project: {response.status_code}")
            print(response.json())
            return None
            
    except Exception as e:
        print(f"❌ Error creating project: {e}")
        return None

def push_to_gitlab(project):
    """Push the code to GitLab"""
    
    if not project:
        return False
    
    print("\n" + "=" * 50)
    print("Configuring Git and Pushing Code")
    print("=" * 50)
    
    # Choose connection method
    print("\nChoose connection method:")
    print("1. HTTPS (uses the same token)")
    print("2. SSH (requires SSH key setup)")
    choice = input("Enter choice (1 or 2): ").strip() or "1"
    
    if choice == "1":
        remote_url = project['http_url_to_repo']
        # Configure git to use token for authentication
        # Extract username from URL
        import re
        match = re.search(r'https://gitlab.com/([^/]+)/', project['web_url'])
        if match:
            username = match.group(1)
            # Modify URL to include token
            remote_url = remote_url.replace('https://', f'https://oauth2:{token}@')
    else:
        remote_url = project['ssh_url_to_repo']
        print("\nMake sure your SSH key is added to GitLab:")
        print("https://gitlab.com/-/profile/keys")
        input("Press Enter when ready...")
    
    try:
        # Add remote
        print(f"\nAdding remote: {remote_url.replace(token, '***') if 'oauth2' in remote_url else remote_url}")
        subprocess.run(["git", "remote", "add", "origin", remote_url], 
                      capture_output=True, text=True)
        
        # If remote already exists, update it
        subprocess.run(["git", "remote", "set-url", "origin", remote_url],
                      capture_output=True, text=True)
        
        # Push to GitLab
        print("Pushing to GitLab (this may take a moment)...")
        result = subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Code pushed successfully!")
            print(f"\n🎉 Your project is now live at:")
            print(f"   {project['web_url']}")
            return True
        else:
            print(f"❌ Push failed: {result.stderr}")
            print("\nYou can try pushing manually with:")
            print("  git push -u origin main")
            return False
            
    except Exception as e:
        print(f"❌ Error pushing code: {e}")
        return False

if __name__ == "__main__":
    print("ASI:BUILD GitLab Deployment Tool\n")
    
    # Check if we're in a git repository
    if not os.path.exists(".git"):
        print("❌ Not in a git repository. Please run from the ASI_BUILD directory.")
        sys.exit(1)
    
    # Create project
    project = create_gitlab_project()
    
    if project:
        # Push code
        push_to_gitlab(project)
        
        print("\n" + "=" * 50)
        print("Setup Complete!")
        print("=" * 50)
        print("\nNext steps:")
        print("1. Visit your project page")
        print("2. Configure CI/CD pipelines")
        print("3. Add team members")
        print("4. Set up project settings")
    else:
        print("\nProject creation failed. Please check your token and try again.")