"""Test script for FastAPI app."""

import os
os.environ["OPENAI_API_KEY"] = "test-key-for-import-only"

from fastapi.testclient import TestClient
from src.voice.app import app

def test_app():
    client = TestClient(app)
    
    # Test 1: Root endpoint
    print("Test 1: Root endpoint...")
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    print(f"  Service: {data['service']}")
    print(f"  Status: {data['status']}")
    
    # Test 2: Health check
    print("\nTest 2: Health check endpoint...")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    print(f"  Status: {data['status']}")
    print(f"  Model: {data['config']['realtime_model']}")
    
    # Test 3: Twilio voice webhook (TwiML response)
    print("\nTest 3: Twilio voice webhook...")
    response = client.post("/twilio/voice", data={
        "CallSid": "CA123456",
        "From": "+15551234567"
    })
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    print(f"  Content-Type: {response.headers['content-type']}")
    print(f"  Contains <Stream>: {'<Stream' in response.text}")
    print(f"  Contains <Connect>: {'<Connect>' in response.text}")
    
    # Test 4: Active calls endpoint
    print("\nTest 4: Active calls endpoint...")
    response = client.get("/calls")
    assert response.status_code == 200
    data = response.json()
    print(f"  Active calls: {len(data['active_calls'])}")
    
    # Test 5: Call not found
    print("\nTest 5: Call not found (404)...")
    response = client.get("/calls/nonexistent")
    assert response.status_code == 404
    print(f"  Status: 404 (as expected)")
    
    print("\n" + "="*50)
    print("All FastAPI app tests passed!")
    print("="*50)


if __name__ == "__main__":
    test_app()
