"""Greeting and small-talk detection.

The Foundry workflow's manager agent is tuned for routing real research
questions and rejects anything else with a harsh `[ROUTE:NONE]` rejection
("I can only assist with TechCorp internal policy questions or current industry
research."). That's a bad first-touch experience when a user just says "hi".

We intercept obvious greetings, thanks, goodbyes, and identity prompts in the
API layer and reply with a friendly canned message that points the user toward
what Orchestrix actually does — no Foundry call, no session persistence.
"""

from __future__ import annotations

import re


GREETING_REPLY = (
    "Hi there! 👋 I'm **Orchestrix**, your enterprise research assistant.\n\n"
    "I can help you with:\n\n"
    "- **Internal policy questions** — leave, benefits, HR, IT and other "
    "TechCorp policies\n"
    "- **Current industry research** — market trends, news and external "
    "context from the open web\n"
    "- **Combined queries** — when you need both internal and external "
    "information in a single answer\n\n"
    "What would you like to look into today?"
)

THANKS_REPLY = (
    "You're welcome! Is there anything else you'd like me to research?"
)

BYE_REPLY = (
    "Goodbye! I'll keep your conversations available — come back any time."
)


_GREETINGS = {
    "hi", "hello", "hey", "yo", "hola", "sup", "greetings", "howdy",
    "good morning", "good afternoon", "good evening", "good day",
    "hi there", "hello there", "hey there",
    "how are you", "how are you doing", "how's it going", "hows it going",
    "what's up", "whats up",
}

_THANKS = {
    "thanks", "thank you", "thx", "ty",
    "thanks a lot", "thank you so much", "thanks so much", "much appreciated",
}

_BYE = {
    "bye", "goodbye", "see you", "see ya", "later", "cya", "good night",
}

_IDENTITY = {
    "who are you", "what are you", "what can you do", "what do you do",
    "help", "what are your capabilities", "capabilities",
    "introduce yourself", "tell me about yourself",
}


def _normalize(message: str) -> str:
    s = message.strip().lower()
    s = re.sub(r"^[^\w]+|[^\w]+$", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def detect_canned_reply(message: str) -> str | None:
    """Return a friendly canned reply for greetings / small talk, else None."""
    norm = _normalize(message)
    if not norm or len(norm) > 60:
        return None
    if norm in _THANKS:
        return THANKS_REPLY
    if norm in _BYE:
        return BYE_REPLY
    if norm in _GREETINGS or norm in _IDENTITY:
        return GREETING_REPLY
    return None
