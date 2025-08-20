#!/usr/bin/env python3
"""
Change GitLab project visibility to private
"""

import requests

TOKEN = "glpat-GfRr5U6UqwvTHuxPgL6j2W86MQp1OmhvdHY3Cw.01.121pxjte3"
PROJECT_ID = "73296605"  # The project ID from the creation

headers = {
    "PRIVATE-TOKEN": TOKEN,
    "Content-Type": "application/json"
}

print("Changing project visibility to PRIVATE...")

data = {
    "visibility": "private"
}

response = requests.put(
    f"https://gitlab.com/api/v4/projects/{PROJECT_ID}",
    headers=headers,
    json=data
)

if response.status_code == 200:
    print("✅ Project is now PRIVATE!")
    print("Only you can access it at: https://gitlab.com/kenny888ag/asi-build")
else:
    print(f"Status code: {response.status_code}")
    print(response.json())