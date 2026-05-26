from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models import Session, Message, User
from app.schemas import ChatRequest, ChatResponse, SessionOut, SessionDetail
from app.services.foundry import call_research_agent
from app.services.auth import get_current_user
from app.services.greetings import detect_canned_reply
from datetime import datetime
import uuid

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # Short-circuit greetings / small-talk on the FIRST message of a chat
        # so the Foundry manager agent doesn't reject "hi" with its harsh
        # out-of-scope rejection. Not persisted — these are one-off intros and
        # shouldn't clutter the user's session list. Once they ask a real
        # question, Foundry creates the conversation and normal flow resumes.
        if request.session_id is None:
            canned = detect_canned_reply(request.message)
            if canned is not None:
                return ChatResponse(
                    response=canned,
                    agent_used="none",
                    session_id="",
                    message_id=str(uuid.uuid4()),
                )

        result = await call_research_agent(
            message=request.message,
            thread_id=request.session_id,
        )

        session_id = result["thread_id"]
        session = db.query(Session).filter(
            Session.id == session_id, Session.user_id == user.id
        ).first()
        if not session:
            title = request.message[:80] + ("..." if len(request.message) > 80 else "")
            session = Session(
                id=session_id,
                user_id=user.id,
                title=title,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(session)

        user_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=request.message,
            created_at=datetime.utcnow(),
        )
        db.add(user_msg)

        assistant_msg_id = str(uuid.uuid4())
        assistant_msg = Message(
            id=assistant_msg_id,
            session_id=session_id,
            role="assistant",
            content=result["response"],
            agent_used=result["agent_used"],
            created_at=datetime.utcnow(),
        )
        db.add(assistant_msg)

        session.updated_at = datetime.utcnow()
        session.message_count = (session.message_count or 0) + 1
        db.commit()

        return ChatResponse(
            response=result["response"],
            agent_used=result["agent_used"],
            session_id=session_id,
            message_id=assistant_msg_id,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(Session)
        .filter(Session.user_id == user.id)
        .order_by(Session.updated_at.desc())
        .limit(50)
        .all()
    )


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(Session).filter(
        Session.id == session_id, Session.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(Session).filter(
        Session.id == session_id, Session.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"deleted": True}
