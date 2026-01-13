import os
import sys
import json
import base64

try:
    import requests
except ImportError:
    print("requests module not available in this context")
    sys.exit(1)

# Configuration from environment
CONFLUENCE_URL = os.environ.get('JIRA_URL', '').replace('/jira', '').rstrip('/')
EMAIL = os.environ.get('ATLASSIAN_USER_EMAIL')
API_TOKEN = os.environ.get('ATLASSIAN_API_TOKEN')
PAGE_ID = "73294938154"

if not all([CONFLUENCE_URL, EMAIL, API_TOKEN]):
    print("Missing required environment variables")
    sys.exit(1)

# Create authentication header
auth_string = f"{EMAIL}:{API_TOKEN}"
auth_bytes = auth_string.encode('ascii')
base64_auth = base64.b64encode(auth_bytes).decode('ascii')

headers = {
    "Authorization": f"Basic {base64_auth}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Test Confluence API v2 - Get page in ADF format
print(f"Fetching Confluence page {PAGE_ID}...")
print(f"URL: {CONFLUENCE_URL}/wiki/api/v2/pages/{PAGE_ID}")

url = f"{CONFLUENCE_URL}/wiki/api/v2/pages/{PAGE_ID}"
params = {
    "body-format": "atlas_doc_format"
}

response = requests.get(url, headers=headers, params=params)

print(f"\nResponse Status: {response.status_code}")
print(f"Response Headers: {dict(response.headers)}")

if response.status_code == 200:
    data = response.json()
    print(f"\n=== Confluence Page Data ===")
    print(f"Page ID: {data.get('id')}")
    print(f"Title: {data.get('title')}")
    print(f"Status: {data.get('status')}")

    # Save full response
    with open('confluence_page_response.json', 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nFull response saved to: confluence_page_response.json")

    # Check for ADF content
    if 'body' in data:
        print(f"\nBody format available: {list(data['body'].keys())}")
        if 'atlas_doc_format' in data['body']:
            adf_content = data['body']['atlas_doc_format']
            print(f"ADF representation: {adf_content.get('representation')}")
            with open('confluence_page_adf.json', 'w') as f:
                json.dump(json.loads(adf_content['value']), f, indent=2)
            print(f"ADF content saved to: confluence_page_adf.json")
else:
    print(f"\nError Response: {response.text}")
