#!/bin/bash

# GitLab Push Script for ASI:BUILD
# 
# Before running this script:
# 1. Create a new project on GitLab.com
# 2. Copy the repository URL (HTTPS or SSH)
# 3. Replace YOUR_GITLAB_USERNAME and YOUR_PROJECT_NAME below

echo "==================================="
echo "ASI:BUILD GitLab Push Setup"
echo "==================================="
echo ""
echo "This script will help you push the ASI:BUILD framework to GitLab."
echo ""
echo "Prerequisites:"
echo "1. You must have a GitLab account"
echo "2. You must create a new project on GitLab first"
echo "3. You'll need the repository URL"
echo ""

read -p "Enter your GitLab username: " GITLAB_USERNAME
read -p "Enter your project name (default: asi-build): " PROJECT_NAME
PROJECT_NAME=${PROJECT_NAME:-asi-build}

echo ""
echo "Choose connection method:"
echo "1. HTTPS (easier, requires username/password)"
echo "2. SSH (more secure, requires SSH key setup)"
read -p "Enter choice (1 or 2): " CONNECTION_METHOD

if [ "$CONNECTION_METHOD" = "1" ]; then
    REMOTE_URL="https://gitlab.com/${GITLAB_USERNAME}/${PROJECT_NAME}.git"
    echo ""
    echo "You'll be prompted for your GitLab username and password when pushing."
    echo "Consider using a Personal Access Token instead of your password:"
    echo "https://gitlab.com/-/profile/personal_access_tokens"
elif [ "$CONNECTION_METHOD" = "2" ]; then
    REMOTE_URL="git@gitlab.com:${GITLAB_USERNAME}/${PROJECT_NAME}.git"
    echo ""
    echo "Make sure you have added your SSH key to GitLab:"
    echo "https://gitlab.com/-/profile/keys"
else
    echo "Invalid choice. Exiting."
    exit 1
fi

echo ""
echo "Remote URL will be: $REMOTE_URL"
echo ""
read -p "Is this correct? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Setup cancelled."
    exit 1
fi

# Add the remote
echo "Adding GitLab remote..."
git remote add origin "$REMOTE_URL" 2>/dev/null || git remote set-url origin "$REMOTE_URL"

# Show the remote
echo "Remote configured:"
git remote -v

echo ""
echo "Ready to push!"
echo ""
echo "To push your code to GitLab, run:"
echo "  git push -u origin main"
echo ""
echo "If you're using HTTPS, you'll be prompted for credentials."
echo "If you're using SSH, make sure your SSH key is configured."
echo ""
read -p "Push now? (y/n): " PUSH_NOW

if [ "$PUSH_NOW" = "y" ]; then
    echo "Pushing to GitLab..."
    git push -u origin main
    echo ""
    echo "✅ Push complete!"
    echo ""
    echo "Your project should now be available at:"
    echo "https://gitlab.com/${GITLAB_USERNAME}/${PROJECT_NAME}"
else
    echo ""
    echo "You can push later using:"
    echo "  git push -u origin main"
fi