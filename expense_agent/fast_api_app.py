import base64
import json
import logging
from typing import Any
import os

from fastapi import FastAPI, Request, HTTPException

# Set telemetry to False as requested
os.environ["OTEL_TO_CLOUD"] = "False"

# Standard Python logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from expense_agent.agent import workflow
from google.adk import Context

app = FastAPI(title="Ambient Expense Agent")

@app.post("/apps/expense_agent/trigger/pubsub")
async def pubsub_trigger(request: Request):
    """Webhook endpoint for Pub/Sub events."""
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse incoming JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    message = body.get("message", {})
    subscription = body.get("subscription", "unknown-sub")

    # Normalize fully-qualified subscription path down to a short name
    if "/" in subscription:
        session_id = subscription.split("/")[-1]
    else:
        session_id = subscription

    logger.info(f"Received Pub/Sub message for session: {session_id}")

    encoded_data = message.get("data")
    if not encoded_data:
        raise HTTPException(status_code=400, detail="Missing message.data")

    try:
        # Pub/Sub payload is base64 encoded
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_str = decoded_bytes.decode("utf-8")
        payload = json.loads(decoded_str)
    except Exception as e:
        logger.error(f"Failed to decode or parse base64 payload: {e}")
        # Pass it as is in case parse_event handles it differently
        payload = {"data": encoded_data}

    logger.info(f"Triggering workflow for session {session_id} with payload: {payload}")

    try:
        # Run the workflow
        ctx = Context(id=session_id)
        async for event in workflow.run(ctx=ctx, node_input=payload):
            pass
        logger.info(f"Workflow execution completed for session {session_id}")
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
