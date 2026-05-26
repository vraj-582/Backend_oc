import asyncio
import re
from azure.ai.projects import AIProjectClient
from azure.core.credentials import AzureKeyCredential
from app.config import settings

# ---------------------------------------------------------------------------
# Module-level singletons — created once, reused across all requests.
# Uses API key auth instead of managed identity for simpler deployment.
# ---------------------------------------------------------------------------
_credential = AzureKeyCredential(settings.AZURE_API_KEY)
_project_client = AIProjectClient(
    endpoint=settings.AZURE_PROJECT_ENDPOINT,
    credential=_credential,
)
_openai_client = _project_client.get_openai_client()


# ---------------------------------------------------------------------------
# Agent detection — reads workflow_action item action_ids from stream events.
# IDs come directly from the workflow YAML nodes:
#   knowledge-node  → ROUTE:INTERNAL path
#   web-node        → ROUTE:WEB path
#   knowledge-both  → ROUTE:BOTH path (knowledge leg)
#   web-both        → ROUTE:BOTH path (web leg)
#   rejection_message → out-of-scope (Else branch)
# ---------------------------------------------------------------------------
_ROUTE_PATTERN = re.compile(r"^\[ROUTE:(INTERNAL|WEB|BOTH)\]", re.IGNORECASE)


def _detect_agent_from_actions(action_ids: list[str]) -> str:
    has_knowledge = any(a in ("knowledge-node", "knowledge-both") for a in action_ids)
    has_web       = any(a in ("web-node",       "web-both")       for a in action_ids)

    if has_knowledge and has_web:
        return "both"
    elif has_knowledge:
        return "knowledge"
    elif has_web:
        return "web"
    else:
        return "none"


def _is_routing_text(text: str) -> bool:
    """Return True if the text is the Manager-agent routing decision
    (e.g. '[ROUTE:BOTH]\n[INTERNAL_QUESTION]...[WEB_QUESTION]...').
    These should be filtered out of the final user-facing response."""
    stripped = text.strip()
    return bool(_ROUTE_PATTERN.match(stripped))


# ---------------------------------------------------------------------------
# Synchronous workflow call — offloaded to a thread pool by the async wrapper.
# ---------------------------------------------------------------------------
def _call_workflow_sync(message: str, conversation_id: str | None) -> dict:
    """
    Calls the published Research-agent Foundry workflow via the OpenAI
    responses API with streaming.

    conversation_id=None  → creates a new conversation (new session)
    conversation_id=<id>  → continues an existing conversation (multi-turn)

    The workflow streams multiple output_text.done events:
      1. Manager-agent routing decision  ([ROUTE:XXX] …) — filtered out
      2. Knowledge-agent response         (if INTERNAL or BOTH)
      3. Web-agent response               (if WEB or BOTH)

    We collect #2 and #3, join them with a divider, and return.
    """
    if not conversation_id:
        conversation    = _openai_client.conversations.create()
        conversation_id = conversation.id

    action_ids:     list[str] = []
    response_parts: list[str] = []

    stream = _openai_client.responses.create(
        conversation=conversation_id,
        extra_body={
            "agent_reference": {
                "name": settings.FOUNDRY_WORKFLOW_NAME,
                "type": "agent_reference",
            }
        },
        input=message,
        stream=True,
    )

    for event in stream:
        event_type = getattr(event, "type", "")

        # Complete text for one output item
        if event_type == "response.output_text.done":
            text = getattr(event, "text", "") or ""
            # Skip the Manager-agent routing decision
            if text.strip() and not _is_routing_text(text):
                response_parts.append(text.strip())

        # Workflow action node started — capture which agent node ran
        elif event_type == "response.output_item.added":
            item = getattr(event, "item", None)
            if item and getattr(item, "type", None) == "workflow_action":
                action_id = getattr(item, "action_id", "")
                if action_id:
                    action_ids.append(action_id)

        # Detect workflow failure
        elif event_type == "response.failed":
            response_obj = getattr(event, "response", None)
            if response_obj:
                error = getattr(response_obj, "error", None)
                if error:
                    code = getattr(error, "code", "") or ""
                    msg  = getattr(error, "message", "") or ""
                    print(f"[FOUNDRY ERROR] {code}: {msg}")
                    if not response_parts:
                        response_parts.append(
                            "The research workflow is temporarily unavailable. "
                            "Please try again in a few minutes. "
                            f"(Error: {code})"
                        )

    # Join all agent response parts with a section divider
    agent_used = _detect_agent_from_actions(action_ids)

    if len(response_parts) > 1 and agent_used == "both":
        # For BOTH routes: label each section clearly
        final_text = (
            "**Internal Knowledge:**\n\n"
            + response_parts[0]
            + "\n\n---\n\n"
            + "**Web Research:**\n\n"
            + response_parts[1]
        )
    elif response_parts:
        final_text = "\n\n".join(response_parts)
    else:
        final_text = "No response received from workflow."

    return {
        "response":        final_text,
        "agent_used":      agent_used,
        "conversation_id": conversation_id,
    }


# ---------------------------------------------------------------------------
# Public async interface — called by the FastAPI router (chat.py).
# ---------------------------------------------------------------------------
async def call_research_agent(message: str, thread_id: str | None = None) -> dict:
    """
    Async wrapper around the blocking Foundry workflow call.
    thread_id maps 1-to-1 with conversation_id on the Foundry side.
    """
    result = await asyncio.to_thread(_call_workflow_sync, message, thread_id)
    return {
        "response":   result["response"],
        "agent_used": result["agent_used"],
        "thread_id":  result["conversation_id"],
    }
