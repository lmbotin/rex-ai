#!/usr/bin/env python3
"""
Run script for the FNOL Voice Agent.

Usage:
    python run_voice_agent.py

Make sure to:
1. Copy .env.example to .env and fill in your API keys
2. Start ngrok: ngrok http 8000
3. Update PUBLIC_BASE_URL and PUBLIC_WSS_BASE_URL in .env with ngrok URLs
4. Configure your Twilio phone number webhook to POST to {PUBLIC_BASE_URL}/twilio/voice
"""

import logging
import os
import sys

# Configure logging VERY early, before any other imports that might use it
# This suppresses noisy debug output from third-party libraries
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("websockets.client").setLevel(logging.WARNING)
logging.getLogger("websockets.server").setLevel(logging.WARNING)
logging.getLogger("python_multipart").setLevel(logging.WARNING)
logging.getLogger("python_multipart.multipart").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def main():
    """Run the voice agent server."""
    import uvicorn
    from src.utils.config import settings
    
    print("=" * 60)
    print("Gana FNOL Voice Agent")
    print("=" * 60)
    print(f"Server: http://{settings.host}:{settings.port}")
    print(f"Public URL: {settings.public_base_url}")
    print(f"WebSocket URL: {settings.public_wss_base_url}")
    print(f"OpenAI Model: {settings.openai_realtime_model}")
    print(f"Voice: {settings.openai_realtime_voice}")
    print("=" * 60)
    print()
    print("Endpoints:")
    print(f"  - Health: http://{settings.host}:{settings.port}/health")
    print(f"  - Twilio Voice: POST {settings.public_base_url}/twilio/voice")
    print(f"  - Twilio Stream: WS {settings.public_wss_base_url}/twilio/stream")
    print(f"  - Active Calls: http://{settings.host}:{settings.port}/calls")
    print()
    print("Configure your Twilio phone number webhook to:")
    print(f"  {settings.public_base_url}/twilio/voice")
    print()
    
    # Use "info" log level for uvicorn to avoid verbose websocket frame logging
    # Even in debug mode, the frame-by-frame logging is too noisy
    uvicorn.run(
        "src.voice.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",  # Always use info to avoid verbose frame logging
    )


if __name__ == "__main__":
    main()
