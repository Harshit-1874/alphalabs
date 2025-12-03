"""
Test script for PUT /api/users/me endpoint.

This script tests the timezone update functionality by:
1. Creating a test request to the endpoint
2. Verifying the response
"""
import requests
import json

# Test endpoint
BASE_URL = "http://localhost:5000"
ENDPOINT = f"{BASE_URL}/api/users/me"

# Test data
test_data = {
    "timezone": "America/New_York"
}

print("Testing PUT /api/users/me endpoint...")
print(f"URL: {ENDPOINT}")
print(f"Request body: {json.dumps(test_data, indent=2)}")
print()

# Note: This will fail without proper authentication
# This is just to verify the endpoint exists and returns the expected error
try:
    response = requests.put(ENDPOINT, json=test_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 401:
        print("\n✅ Endpoint exists and requires authentication (expected)")
    elif response.status_code == 200:
        print("\n✅ Endpoint works successfully!")
    else:
        print(f"\n❌ Unexpected status code: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")

# Test with invalid timezone
print("\n" + "="*60)
print("Testing with invalid timezone...")
invalid_data = {
    "timezone": "Invalid/Timezone"
}

try:
    response = requests.put(ENDPOINT, json=invalid_data, headers={"Authorization": "Bearer fake_token"})
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
