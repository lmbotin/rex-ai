"""
FastAPI application for the FNOL Voice Agent.

Provides:
- TwiML webhook endpoint for Twilio call handling
- WebSocket endpoint for Twilio Media Streams
- Health check and status endpoints
"""

# IMPORTANT: Configure logging FIRST, before any other imports
# This ensures verbose libraries don't spam debug logs
import logging

# Reduce noise from verbose libraries - set this BEFORE they're imported
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("websockets.client").setLevel(logging.WARNING)
logging.getLogger("websockets.server").setLevel(logging.WARNING)
logging.getLogger("python_multipart").setLevel(logging.WARNING)
logging.getLogger("python_multipart.multipart").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)

import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, JSONResponse

from ..utils.config import settings
from ..storage import save_claim, get_claim_store
from .bridge import AudioBridge

# Claim processing (imported lazily to avoid startup delay)
_claim_processor = None

def get_claim_processor():
    """Lazy-load the claim processor."""
    global _claim_processor
    if _claim_processor is None:
        from ..routing import get_claim_processor as _get_processor
        _claim_processor = _get_processor()
    return _claim_processor

# Now configure logging properly
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Store active calls for monitoring
active_calls: dict[str, AudioBridge] = {}

# Store processed claims (in production, use a database)
processed_claims: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting FNOL Voice Agent server...")
    logger.info(f"Public URL: {settings.public_base_url}")
    logger.info(f"WebSocket URL: {settings.public_wss_base_url}")
    yield
    logger.info("Shutting down FNOL Voice Agent server...")
    # Clean up any remaining calls
    active_calls.clear()


app = FastAPI(
    title="Gana FNOL Voice Agent",
    description="Real-time voice agent for insurance claim intake",
    version="1.0.0",
    lifespan=lifespan,
)


# =============================================================================
# Health Check Endpoints
# =============================================================================


@app.get("/")
async def root():
    """Root endpoint - basic health check."""
    return {
        "service": "Gana FNOL Voice Agent",
        "status": "running",
        "active_calls": len(active_calls),
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "active_calls": len(active_calls),
        "config": {
            "realtime_model": settings.openai_realtime_model,
            "voice": settings.openai_realtime_voice,
            "public_url": settings.public_base_url,
        },
    }


# =============================================================================
# Twilio Webhook Endpoints
# =============================================================================


@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    """
    Twilio voice webhook - returns TwiML to start a Media Stream.
    
    This is called when Twilio receives an incoming call to your number.
    It returns TwiML that:
    1. Optionally plays a welcome message
    2. Connects to a bidirectional Media Stream
    """
    # Get call info from Twilio's POST data
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    from_number = form_data.get("From", "unknown")
    
    logger.info(f"Incoming call: {call_sid} from {from_number}")
    
    # Build the stream URL
    stream_url = settings.twilio_stream_url
    
    # Generate TwiML response
    # Note: We use <Connect><Stream> for bidirectional streaming
    # No <Say> element - the AI agent will greet naturally via the realtime API
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{stream_url}">
            <Parameter name="callSid" value="{call_sid}" />
        </Stream>
    </Connect>
</Response>"""
    
    return Response(content=twiml, media_type="application/xml")


@app.post("/twilio/status")
async def twilio_status(request: Request):
    """
    Twilio status callback - called when call status changes.
    
    Useful for tracking call completion and cleaning up resources.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    call_status = form_data.get("CallStatus")
    
    logger.info(f"Call status update: {call_sid} -> {call_status}")
    
    # Clean up if call ended
    if call_status in ("completed", "failed", "busy", "no-answer", "canceled"):
        if call_sid in active_calls:
            bridge = active_calls.pop(call_sid)
            logger.info(f"Call {call_sid} ended. FNOL data collected.")
    
    return Response(status_code=200)


# =============================================================================
# WebSocket Endpoint for Media Streams
# =============================================================================


@app.websocket("/twilio/stream")
async def twilio_stream(websocket: WebSocket):
    """
    WebSocket endpoint for Twilio Media Streams.
    
    Handles bidirectional audio streaming between Twilio and OpenAI Realtime API.
    """
    await websocket.accept()
    
    call_sid: Optional[str] = None
    bridge: Optional[AudioBridge] = None
    
    def register_call(sid: str, br: AudioBridge) -> None:
        """Callback to register call in active_calls when call_sid is known."""
        nonlocal call_sid
        call_sid = sid
        active_calls[sid] = br
        logger.info(f"Call {sid} registered in active_calls")
    
    try:
        # Create a unique ID for this connection
        connection_id = str(uuid.uuid4())[:8]
        logger.info(f"WebSocket connection opened: {connection_id}")
        
        # Initialize the audio bridge with callback to register in active_calls
        bridge = AudioBridge(on_call_started=register_call)
        
        # Run the bridge (this handles the full call lifecycle)
        await bridge.run(websocket)
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {call_sid or 'unknown'}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Clean up - remove from active_calls
        if call_sid and call_sid in active_calls:
            del active_calls[call_sid]
            logger.info(f"Call {call_sid} removed from active_calls")
        
        # Log final FNOL state and process through LangGraph workflow
        if bridge:
            call_id = bridge.call_sid or "unknown"
            logger.info(f"Call {call_id} completed")
            logger.info(f"FNOL Summary:\n{bridge.get_fnol_summary()}")
            
            # Get the claim data first
            fnol_data = bridge.get_fnol_data()
            logger.info(f"FNOL Data extracted: {list(fnol_data.keys())}")
            logger.info(f"Claimant: {fnol_data.get('claimant', {})}")
            logger.info(f"Incident: {fnol_data.get('incident', {})}")
            logger.info(f"Property Damage: {fnol_data.get('property_damage', {})}")
            
            # Always try to save the claim data, even if processing fails
            claim_id = None
            try:
                claim_id = save_claim(
                    claim_data=fnol_data,
                    source="voice",
                    call_sid=call_id,
                )
                logger.info(f"✅ Claim saved to database with ID: {claim_id}")
            except Exception as db_error:
                logger.error(f"❌ Failed to save claim to database: {db_error}")
                import traceback
                traceback.print_exc()
            
            # Now try to process the claim
            try:
                processor = get_claim_processor()
                result = await processor.process_claim(fnol_data, call_id)
                
                # Store in memory for API access
                processed_claims[call_id] = {
                    "fnol_data": fnol_data,
                    "processing_result": result.to_dict(),
                }
                
                # Update the database with processing results
                if claim_id:
                    try:
                        store = get_claim_store()
                        store.save_processing_result(
                            claim_id=claim_id,
                            validation_result={
                                "is_complete": result.is_complete,
                                "missing_fields": result.missing_fields,
                                "validation_errors": result.validation_errors,
                            },
                            fraud_result={
                                "fraud_score": result.fraud_score,
                                "fraud_indicators": result.fraud_indicators,
                            },
                            routing_result={
                                "priority": result.priority.value if hasattr(result.priority, 'value') else str(result.priority),
                                "routing_decision": result.routing_decision.value if hasattr(result.routing_decision, 'value') else str(result.routing_decision),
                                "routing_reason": result.routing_reason,
                                "final_status": result.final_status,
                                "next_actions": result.next_actions,
                            },
                        )
                        store.update_status(claim_id, result.final_status)
                        logger.info(f"✅ Processing results saved for claim {claim_id}")
                    except Exception as db_error:
                        logger.error(f"❌ Failed to save processing results: {db_error}")
                
                logger.info(f"Claim processed: {result.routing_decision} - {result.routing_reason}")
                logger.info(f"Fraud score: {result.fraud_score:.2f}, Priority: {result.priority}")
                logger.info(f"Next actions: {result.next_actions}")
            except Exception as e:
                logger.error(f"❌ Failed to process claim through workflow: {e}")
                import traceback
                traceback.print_exc()


# =============================================================================
# API Endpoints for Monitoring and Management
# =============================================================================


@app.get("/calls")
async def list_calls():
    """List all active calls."""
    return {
        "active_calls": [
            {
                "call_sid": call_sid,
                "completion": bridge.fnol_state.get_completion_percentage(),
            }
            for call_sid, bridge in active_calls.items()
        ]
    }


@app.get("/calls/{call_sid}")
async def get_call(call_sid: str):
    """Get details for a specific call."""
    if call_sid not in active_calls:
        return JSONResponse(
            status_code=404,
            content={"error": "Call not found"},
        )
    
    bridge = active_calls[call_sid]
    return {
        "call_sid": call_sid,
        "completion": bridge.fnol_state.get_completion_percentage(),
        "summary": bridge.get_fnol_summary(),
        "fnol_data": bridge.get_fnol_data(),
    }


@app.get("/calls/{call_sid}/fnol")
async def get_call_fnol(call_sid: str):
    """Get the FNOL data for a specific call."""
    if call_sid not in active_calls:
        return JSONResponse(
            status_code=404,
            content={"error": "Call not found"},
        )
    
    bridge = active_calls[call_sid]
    return bridge.get_fnol_data()


# =============================================================================
# LangGraph Processed Claims Endpoints
# =============================================================================


@app.get("/processed")
async def list_processed_claims():
    """List all processed claims."""
    return {
        "processed_claims": [
            {
                "call_sid": call_sid,
                "routing_decision": data["processing_result"]["routing_decision"],
                "fraud_score": data["processing_result"]["fraud_score"],
                "priority": data["processing_result"]["priority"],
                "status": data["processing_result"]["final_status"],
            }
            for call_sid, data in processed_claims.items()
        ]
    }


@app.get("/processed/{call_sid}")
async def get_processed_claim(call_sid: str):
    """Get full details of a processed claim."""
    if call_sid not in processed_claims:
        return JSONResponse(
            status_code=404,
            content={"error": "Processed claim not found"},
        )
    
    return processed_claims[call_sid]


@app.post("/process")
async def process_fnol_manually(fnol_data: dict):
    """
    Manually process an FNOL through the LangGraph workflow.
    
    Useful for testing or reprocessing claims.
    """
    try:
        processor = get_claim_processor()
        result = await processor.process_claim(fnol_data, call_sid="manual")
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Processing failed: {str(e)}"},
        )


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Run the FastAPI server."""
    import uvicorn
    
    uvicorn.run(
        "src.voice.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )


if __name__ == "__main__":
    main()
