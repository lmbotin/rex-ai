"""
Voice module for FNOL intake via phone calls.

This module provides real-time voice interaction using:
- Twilio Media Streams for telephony
- OpenAI Realtime API for speech-to-speech processing
"""

from .app import app, main
from .bridge import AudioBridge
from .openai_realtime import OpenAIRealtimeClient

__all__ = ["app", "main", "AudioBridge", "OpenAIRealtimeClient"]
