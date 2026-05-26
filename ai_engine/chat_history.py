"""
Chat History Store — Persistent in-process storage for AI Analyst conversations.
Manages sessions (named by date), per-session message lists, and conversation context.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from nicegui import app

logger = logging.getLogger(__name__)

# ─── Storage Key ─────────────────────────────────────────────────
_STORAGE_KEY = 'ai_analyst_sessions'


def _get_sessions() -> Dict[str, Any]:
    """Return the sessions dict from user storage, initialising if missing."""
    sessions = app.storage.user.get(_STORAGE_KEY, {})
    if not isinstance(sessions, dict):
        sessions = {}
    return sessions


def _save_sessions(sessions: Dict[str, Any]):
    app.storage.user[_STORAGE_KEY] = sessions


def _today_key() -> str:
    return datetime.now().strftime('%Y-%m-%d')


# ─── Public API ──────────────────────────────────────────────────

def get_all_sessions() -> List[Dict[str, Any]]:
    """
    Return list of sessions sorted by most-recent first.
    Each item: { id, label, created_at, messages }
    """
    sessions = _get_sessions()
    result = []
    for sid, data in sessions.items():
        result.append({
            'id': sid,
            'label': data.get('label', sid),
            'created_at': data.get('created_at', sid),
            'messages': data.get('messages', [])
        })
    result.sort(key=lambda x: x['created_at'], reverse=True)
    return result


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    sessions = _get_sessions()
    return sessions.get(session_id)


def get_or_create_today_session() -> str:
    """Return today's session ID, creating one if it doesn't exist."""
    sessions = _get_sessions()
    today = _today_key()
    if today not in sessions:
        sessions[today] = {
            'label': datetime.now().strftime('%d %b %Y'),
            'created_at': datetime.now().isoformat(),
            'messages': []
        }
        _save_sessions(sessions)
        logger.info(f"Created new chat session: {today}")
    return today


def create_new_session() -> str:
    """Force create a new session keyed by current timestamp."""
    sessions = _get_sessions()
    sid = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    sessions[sid] = {
        'label': datetime.now().strftime('%d %b %Y · %H:%M'),
        'created_at': datetime.now().isoformat(),
        'messages': []
    }
    _save_sessions(sessions)
    logger.info(f"Created new chat session: {sid}")
    return sid


def append_message(session_id: str, role: str, content: str,
                   sql: Optional[str] = None, data: Optional[list] = None):
    """Append a message to a session, ensuring data is fully JSON-serializable."""
    sessions = _get_sessions()
    if session_id not in sessions:
        sessions[session_id] = {
            'label': datetime.now().strftime('%d %b %Y'),
            'created_at': datetime.now().isoformat(),
            'messages': []
        }

    # Safe sanitization of DuckDB / custom data objects to raw serializable types
    clean_data = None
    if data is not None:
        try:
            if isinstance(data, list):
                clean_data = []
                for row in data:
                    if isinstance(row, dict):
                        clean_row = {}
                        for k, v in row.items():
                            if v is None:
                                clean_row[k] = ""
                            elif isinstance(v, (int, float, str, bool)):
                                clean_row[k] = v
                            else:
                                clean_row[k] = str(v)
                        clean_data.append(clean_row)
                    else:
                        clean_data.append(str(row))
            else:
                clean_data = str(data)
        except Exception as e:
            logger.error(f"Failed to sanitize data in append_message: {e}")
            clean_data = None

    sessions[session_id]['messages'].append({
        'role': role,
        'content': content,
        'sql': sql,
        'data': clean_data,
        'ts': datetime.now().strftime('%H:%M')
    })
    try:
        _save_sessions(sessions)
    except Exception as e:
        logger.error(f"Failed to save sessions after appending message: {e}")


def get_messages(session_id: str) -> List[Dict[str, Any]]:
    sessions = _get_sessions()
    return sessions.get(session_id, {}).get('messages', [])


def delete_session(session_id: str):
    sessions = _get_sessions()
    if session_id in sessions:
        del sessions[session_id]
        _save_sessions(sessions)
        logger.info(f"Deleted session: {session_id}")


def rename_session(session_id: str, new_label: str):
    sessions = _get_sessions()
    if session_id in sessions:
        sessions[session_id]['label'] = new_label
        _save_sessions(sessions)


def build_conversation_context(messages: List[Dict[str, Any]], max_turns: int = 6) -> str:
    """
    Build a concise conversation history string for the LLM.
    Includes last N turns (user + assistant pairs).
    """
    if not messages:
        return ""
    # Take last max_turns messages
    recent = messages[-max_turns:]
    lines = []
    for msg in recent:
        role = "User" if msg['role'] == 'user' else "AI Analyst"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)
