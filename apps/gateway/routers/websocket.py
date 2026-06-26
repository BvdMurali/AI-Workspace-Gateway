"""
AI Workspace Gateway - WebSocket Router
Serves the /ws connection endpoint and handles message exchange lifecycle.
"""

import logging
import uuid
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import ValidationError

from apps.gateway.utils.envelope import MessageEnvelope, create_error_payload
from apps.gateway.services.connection_manager import ConnectionManager

router = APIRouter()
logger = logging.getLogger("gateway")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str = Query("anonymous", alias="clientId")
) -> None:
    """
    Main WebSocket endpoint serving client real-time interaction.
    Orchestrates handshake, ping/pong heartbeats, and topic subscriptions.
    """
    await websocket.accept()
    
    # Resolve ConnectionManager from app state
    container = getattr(websocket.app.state, "container", None)
    if not container:
        # Fallback to parent app scope if mounted
        parent = getattr(websocket.app, "parent", None)
        if parent:
            container = getattr(parent.state, "container", None)
            
    if not container:
        logger.error("DI Container could not be resolved from WebSocket state.")
        await websocket.close()
        return

    connection_manager = container.resolve(ConnectionManager)
    connection_id = f"conn-{uuid.uuid4()}"
    
    # Register the connection
    connection_manager.connect(connection_id, client_id, websocket)

    try:
        while True:
            # Wait for client JSON payloads
            data = await websocket.receive_json()
            
            # Recieved any message -> update heartbeat to prevent idle disconnect
            connection_manager.update_heartbeat(connection_id)
            
            # Parse the incoming envelope
            try:
                envelope = MessageEnvelope.model_validate(data)
            except ValidationError as val_err:
                logger.warning(f"WebSocket received invalid message envelope: {val_err}")
                corr_id = data.get("correlation_id") if isinstance(data, dict) else None
                error_env = MessageEnvelope(
                    type="session.error",
                    correlation_id=corr_id,
                    payload=create_error_payload(
                        code="MESSAGE_ENVELOPE_INVALID",
                        message=f"Message envelope validation failed: {val_err}"
                    )
                )
                await websocket.send_json(error_env.model_dump())
                continue

            # Process infrastructure messages
            if envelope.type == "ping":
                # Respond to ping with a pong, correlating via ping's id
                pong_env = MessageEnvelope(
                    type="pong",
                    correlation_id=envelope.id,
                    payload={}
                )
                await websocket.send_json(pong_env.model_dump())

            elif envelope.type == "subscribe":
                topic = envelope.payload.get("topic")
                if not topic:
                    error_env = MessageEnvelope(
                        type="session.error",
                        correlation_id=envelope.id,
                        payload=create_error_payload("SUBSCRIBE_MISSING_TOPIC", "Subscription payload requires 'topic'")
                    )
                    await websocket.send_json(error_env.model_dump())
                else:
                    connection_manager.subscribe(connection_id, topic)
                    ack_env = MessageEnvelope(
                        type="subscribe.ack",
                        correlation_id=envelope.id,
                        payload={"topic": topic}
                    )
                    await websocket.send_json(ack_env.model_dump())

            elif envelope.type == "unsubscribe":
                topic = envelope.payload.get("topic")
                if not topic:
                    error_env = MessageEnvelope(
                        type="session.error",
                        correlation_id=envelope.id,
                        payload=create_error_payload("UNSUBSCRIBE_MISSING_TOPIC", "Unsubscription payload requires 'topic'")
                    )
                    await websocket.send_json(error_env.model_dump())
                else:
                    connection_manager.unsubscribe(connection_id, topic)
                    ack_env = MessageEnvelope(
                        type="unsubscribe.ack",
                        correlation_id=envelope.id,
                        payload={"topic": topic}
                    )
                    await websocket.send_json(ack_env.model_dump())

            else:
                # Unsupported message type (infrastructure only)
                error_env = MessageEnvelope(
                    type="session.error",
                    correlation_id=envelope.id,
                    payload=create_error_payload(
                        code="UNSUPPORTED_MESSAGE_TYPE",
                        message=f"Infrastructure message type '{envelope.type}' is unsupported."
                    )
                )
                await websocket.send_json(error_env.model_dump())

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected cleanly: {connection_id}")
    except Exception as e:
        logger.error(f"Unhandled exception in WebSocket session '{connection_id}': {e}", exc_info=True)
    finally:
        # Guarantee cleanup on disconnect
        await connection_manager.disconnect(connection_id)
