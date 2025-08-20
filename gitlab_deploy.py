#!/usr/bin/env python3
"""
GitLab Project Creator for ASI:BUILD
"""

import os
import sys
import subprocess
import requests

# GitLab configuration
TOKEN = "glpat-GfRr5U6UqwvTHuxPgL6j2W86MQp1OmhvdHY3Cw.01.121pxjte3"
PROJECT_NAME = "asi-build"
PROJECT_PATH = "asi-build"
DESCRIPTION = "ASI:BUILD - Unified Framework for Artificial Superintelligence"
VISIBILITY = "public"  # Making it public to showcase the project

def create_gitlab_project():
    """Create a new GitLab project using the API"""
    
    print("=" * 50)
    print("Creating ASI:BUILD GitLab Project")
    print("=" * 50)
    
    headers = {
        "PRIVATE-TOKEN": TOKEN,
        "Content-Type": "application/json"
    }
    
    data = {
        "name": PROJECT_NAME,
        "path": PROJECT_PATH,
        "description": DESCRIPTION,
        "visibility": VISIBILITY,
        "initialize_with_readme": False,
        "issues_enabled": True,
        "merge_requests_enabled": True,
        "wiki_enabled": True,
        "snippets_enabled": True,
        "packages_enabled": True,
        "topics": [
            "artificial-intelligence",
            "superintelligence",
            "agi",
            "asi",
            "machine-learning",
            "deep-learning",
            "consciousness",
            "quantum-computing"
        ]
    }
    
    try:
        print(f"\nCreating project '{PROJECT_NAME}'...")
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
            return project
        elif response.status_code == 400 and "has already been taken" in str(response.json()):
            print("Project name already exists. Trying to fetch existing project...")
            # Try to get the existing project
            user_response = requests.get(
                "https://gitlab.com/api/v4/user",
                headers=headers
            )
            if user_response.status_code == 200:
                username = user_response.json()['username']
                project_response = requests.get(
                    f"https://gitlab.com/api/v4/projects/{username}%2F{PROJECT_PATH}",
                    headers=headers
                )
                if project_response.status_code == 200:
                    project = project_response.json()
                    print("✅ Found existing project!")
                    print(f"Project URL: {project['web_url']}")
                    return project
            print("Could not fetch existing project details")
            return None
        else:
            print(f"❌ Failed to create project: {response.status_code}")
            print(response.json())
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def push_to_gitlab(project):
    """Push the code to GitLab"""
    
    if not project:
        return False
    
    print("\n" + "=" * 50)
    print("Pushing Code to GitLab")
    print("=" * 50)
    
    # Use HTTPS with token authentication
    remote_url = project['http_url_to_repo']
    # Add token to URL for authentication
    remote_url = remote_url.replace('https://', f'https://oauth2:{TOKEN}@')
    
    try:
        # Remove existing origin if it exists
        subprocess.run(["git", "remote", "remove", "origin"], 
                      capture_output=True, text=True)
        
        # Add new remote
        print(f"\nAdding remote...")
        result = subprocess.run(["git", "remote", "add", "origin", remote_url], 
                              capture_output=True, text=True)
        
        # Push to GitLab
        print("Pushing to GitLab (this may take a moment due to the large codebase)...")
        result = subprocess.run(
            ["git", "push", "-u", "origin", "main", "--force"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Code pushed successfully!")
            print(f"\n🎉 Your project is now live at:")
            print(f"   {project['web_url']}")
            return True
        else:
            if "Everything up-to-date" in result.stderr or "Everything up-to-date" in result.stdout:
                print("✅ Repository is already up to date!")
                print(f"\n🎉 Your project is live at:")
                print(f"   {project['web_url']}")
                return True
            else:
                print(f"Push output: {result.stdout}")
                print(f"Push errors: {result.stderr}")
                return False
            
    except Exception as e:
        print(f"❌ Error pushing code: {e}")
        return False

if __name__ == "__main__":
    print("ASI:BUILD GitLab Deployment\n")
    
    # Check if we're in a git repository
    if not os.path.exists(".git"):
        print("❌ Not in a git repository. Please run from the ASI_BUILD directory.")
        sys.exit(1)
    
    # Create or find project
    project = create_gitlab_project()
    
    if project:
        # Push code
        if push_to_gitlab(project):
            print("\n" + "=" * 50)
            print("✅ Deployment Complete!")
            print("=" * 50)
            print(f"\nYour ASI:BUILD project is now on GitLab!")
            print(f"Visit: {project['web_url']}")
            print("\nFeatures enabled:")
            print("- Issue tracking")
            print("- Merge requests")
            print("- Wiki documentation")
            print("- CI/CD pipelines")
            print("- Package registry")
    else:
        print("\n❌ Deployment failed. Please check the error messages above.")