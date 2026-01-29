"""
OpenAI Realtime API WebSocket client for speech-to-speech processing.

Handles bidirectional audio streaming with the OpenAI Realtime API,
supporting PCMU audio format for direct Twilio integration.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Callable, Optional

import websockets
from websockets.client import WebSocketClientProtocol

from ..utils.config import settings
from .prompts import VOICE_AGENT_PROMPT_COMPACT

logger = logging.getLogger(__name__)


class RealtimeEventType(str, Enum):
    """OpenAI Realtime API event types."""
    # Session events
    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"
    
    # Input audio events
    INPUT_AUDIO_BUFFER_SPEECH_STARTED = "input_audio_buffer.speech_started"
    INPUT_AUDIO_BUFFER_SPEECH_STOPPED = "input_audio_buffer.speech_stopped"
    INPUT_AUDIO_BUFFER_COMMITTED = "input_audio_buffer.committed"
    
    # Conversation events
    CONVERSATION_ITEM_CREATED = "conversation.item.created"
    CONVERSATION_ITEM_TRUNCATED = "conversation.item.truncated"
    
    # Response events
    RESPONSE_CREATED = "response.created"
    RESPONSE_DONE = "response.done"
    RESPONSE_OUTPUT_ITEM_ADDED = "response.output_item.added"
    RESPONSE_OUTPUT_ITEM_DONE = "response.output_item.done"
    RESPONSE_CONTENT_PART_ADDED = "response.content_part.added"
    RESPONSE_CONTENT_PART_DONE = "response.content_part.done"
    RESPONSE_AUDIO_DELTA = "response.audio.delta"
    RESPONSE_AUDIO_DONE = "response.audio.done"
    RESPONSE_AUDIO_TRANSCRIPT_DELTA = "response.audio_transcript.delta"
    RESPONSE_AUDIO_TRANSCRIPT_DONE = "response.audio_transcript.done"
    RESPONSE_TEXT_DELTA = "response.text.delta"
    RESPONSE_TEXT_DONE = "response.text.done"
    
    # Transcription events
    CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED = (
        "conversation.item.input_audio_transcription.completed"
    )
    CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_FAILED = (
        "conversation.item.input_audio_transcription.failed"
    )
    
    # Error events
    ERROR = "error"
    
    # Rate limit events
    RATE_LIMITS_UPDATED = "rate_limits.updated"


@dataclass
class RealtimeEvent:
    """Represents an event from the OpenAI Realtime API."""
    type: str
    data: dict = field(default_factory=dict)
    
    @property
    def event_type(self) -> Optional[RealtimeEventType]:
        """Get the typed event type if recognized."""
        try:
            return RealtimeEventType(self.type)
        except ValueError:
            return None
    
    @property
    def is_audio_delta(self) -> bool:
        """Check if this is an audio delta event."""
        return self.type == RealtimeEventType.RESPONSE_AUDIO_DELTA
    
    @property
    def is_speech_started(self) -> bool:
        """Check if user started speaking (for barge-in)."""
        return self.type == RealtimeEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED
    
    @property
    def is_transcript_complete(self) -> bool:
        """Check if input transcription is complete."""
        return self.type == RealtimeEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED
    
    @property
    def is_error(self) -> bool:
        """Check if this is an error event."""
        return self.type == RealtimeEventType.ERROR
    
    @property
    def audio_delta(self) -> Optional[str]:
        """Get the base64-encoded audio delta if present."""
        if self.is_audio_delta:
            return self.data.get("delta")
        return None
    
    @property
    def transcript(self) -> Optional[str]:
        """Get the transcript text if present."""
        if self.is_transcript_complete:
            return self.data.get("transcript")
        return None
    
    @property
    def error_message(self) -> Optional[str]:
        """Get the error message if this is an error event."""
        if self.is_error:
            error = self.data.get("error", {})
            return error.get("message", str(error))
        return None


class OpenAIRealtimeClient:
    """
    Client for the OpenAI Realtime API.
    
    Handles WebSocket connection, session configuration, and bidirectional
    audio streaming in PCMU format for Twilio compatibility.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        voice: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the Realtime client.
        
        Args:
            api_key: OpenAI API key (defaults to settings)
            model: Model to use (defaults to settings)
            voice: Voice to use (defaults to settings)
            system_prompt: Custom system prompt (defaults to FNOL prompt)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_realtime_model
        self.voice = voice or settings.openai_realtime_voice
        self.system_prompt = system_prompt or VOICE_AGENT_PROMPT_COMPACT
        
        self._ws: Optional[WebSocketClientProtocol] = None
        self._connected = False
        self._session_id: Optional[str] = None
        
        # Event handlers
        self._on_audio_delta: Optional[Callable[[str], None]] = None
        self._on_speech_started: Optional[Callable[[], None]] = None
        self._on_transcript: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to the Realtime API."""
        return self._connected and self._ws is not None
    
    @property
    def realtime_url(self) -> str:
        """Get the Realtime API WebSocket URL."""
        return f"wss://api.openai.com/v1/realtime?model={self.model}"
    
    def on_audio_delta(self, handler: Callable[[str], None]) -> None:
        """Register handler for audio delta events."""
        self._on_audio_delta = handler
    
    def on_speech_started(self, handler: Callable[[], None]) -> None:
        """Register handler for speech started events (barge-in)."""
        self._on_speech_started = handler
    
    def on_transcript(self, handler: Callable[[str], None]) -> None:
        """Register handler for completed transcripts."""
        self._on_transcript = handler
    
    def on_error(self, handler: Callable[[str], None]) -> None:
        """Register handler for error events."""
        self._on_error = handler
    
    @asynccontextmanager
    async def connect(self):
        """
        Connect to the OpenAI Realtime API.
        
        Usage:
            async with client.connect():
                await client.send_audio(audio_data)
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1",
        }
        
        try:
            logger.info(f"Connecting to OpenAI Realtime API: {self.realtime_url}")
            
            self._ws = await websockets.connect(
                self.realtime_url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=20,
            )
            self._connected = True
            
            # Configure the session
            await self._configure_session()
            
            logger.info("Connected to OpenAI Realtime API")
            yield self
            
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {e}")
            raise
        finally:
            self._connected = False
            if self._ws:
                await self._ws.close()
                self._ws = None
    
    async def _configure_session(self) -> None:
        """Configure the Realtime session after connection."""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self.system_prompt,
                "voice": self.voice,
                # Use G.711 μ-law to match Twilio's audio format (no conversion needed)
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "input_audio_transcription": {
                    "model": "whisper-1",
                },
                "turn_detection": {
                    "type": "server_vad",
                    # Higher threshold = less sensitive to background noise (0.7 is conservative)
                    "threshold": 0.7,
                    # Require 1.5+ seconds of sustained speech before triggering interruption
                    # This prevents the AI from stopping mid-sentence on brief sounds or "uh-huh"
                    "prefix_padding_ms": 1500,
                    # How long to wait for silence before considering speech done
                    "silence_duration_ms": settings.silence_duration_ms,
                    # Automatically create response when user finishes speaking
                    "create_response": True,
                },
                # Temperature for more natural, varied responses
                "temperature": 0.8,
                # No token limit - let her speak as long as needed
                # (Previously 300 was causing mid-sentence cutoffs)
                "max_response_output_tokens": "inf",
            },
        }
        
        await self._send(session_config)
        logger.info(f"OpenAI session configured: voice={self.voice}, model={self.model}, audio=g711_ulaw")
    
    async def _send(self, message: dict) -> None:
        """Send a message to the Realtime API."""
        if not self._ws:
            raise RuntimeError("Not connected to OpenAI Realtime API")
        
        await self._ws.send(json.dumps(message))
    
    async def send_audio(self, audio_b64: str) -> None:
        """
        Send audio data to the Realtime API.
        
        Args:
            audio_b64: Base64-encoded audio data (PCMU from Twilio)
        """
        if not self.is_connected:
            logger.warning("Cannot send audio: not connected")
            return
        
        message = {
            "type": "input_audio_buffer.append",
            "audio": audio_b64,
        }
        await self._send(message)
    
    async def commit_audio(self) -> None:
        """Commit the audio buffer to finalize input."""
        if not self.is_connected:
            return
        
        await self._send({"type": "input_audio_buffer.commit"})
    
    async def cancel_response(self) -> None:
        """Cancel the current response (for barge-in)."""
        if not self.is_connected:
            return
        
        await self._send({"type": "response.cancel"})
        logger.debug("Response cancelled")
    
    async def create_response(self) -> None:
        """Trigger a response from the model."""
        if not self.is_connected:
            return
        
        await self._send({"type": "response.create"})
    
    async def send_text(self, text: str, role: str = "user") -> None:
        """
        Send a text message to the conversation.
        
        Args:
            text: Text content
            role: Role (user or assistant)
        """
        if not self.is_connected:
            return
        
        message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": role,
                "content": [
                    {
                        "type": "input_text",
                        "text": text,
                    }
                ],
            },
        }
        await self._send(message)
    
    async def update_instructions(self, instructions: str) -> None:
        """Update the system instructions mid-session."""
        if not self.is_connected:
            return
        
        await self._send({
            "type": "session.update",
            "session": {
                "instructions": instructions,
            },
        })
    
    async def receive_events(self) -> AsyncIterator[RealtimeEvent]:
        """
        Receive events from the Realtime API.
        
        Yields:
            RealtimeEvent objects for each received event
        """
        if not self._ws:
            raise RuntimeError("Not connected to OpenAI Realtime API")
        
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    event_type = data.get("type", "unknown")
                    
                    event = RealtimeEvent(type=event_type, data=data)
                    
                    # Log important events
                    if event.is_error:
                        logger.error(f"Realtime API error: {event.error_message}")
                        if self._on_error:
                            self._on_error(event.error_message)
                    elif event.is_speech_started:
                        logger.debug("User speech started (barge-in)")
                        if self._on_speech_started:
                            self._on_speech_started()
                    elif event.is_transcript_complete:
                        logger.info(f"Transcript: {event.transcript}")
                        if self._on_transcript:
                            self._on_transcript(event.transcript)
                    elif event.is_audio_delta:
                        if self._on_audio_delta:
                            self._on_audio_delta(event.audio_delta)
                    
                    yield event
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse Realtime message: {e}")
                    
        except asyncio.CancelledError:
            logger.info("Realtime event loop cancelled")
            raise
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Realtime connection closed: {e}")
        except Exception as e:
            logger.error(f"Error receiving Realtime events: {e}")
            raise
    
    async def run_event_loop(self) -> None:
        """
        Run the event loop, dispatching events to registered handlers.
        
        This is a convenience method that processes all events and
        calls the appropriate handlers.
        """
        async for event in self.receive_events():
            # Events are already dispatched in receive_events
            # This method just keeps the loop running
            pass
