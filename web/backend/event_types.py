"""SSE event type definitions for the EBM 5A workflow UI."""

import json
from enum import Enum
from typing import Any, Dict
from pydantic import BaseModel


class EventType(str, Enum):
    WORKFLOW_STARTED = "workflow_started"
    AGENT_STARTED = "agent_started"
    AGENT_LOG = "agent_log"
    AGENT_COMPLETED = "agent_completed"
    JUDGE_COMPLETED = "judge_completed"
    SCHEDULING_DECIDED = "scheduling_decided"
    FASTPATH_TRIGGERED = "fastpath_triggered"
    BACKTRACK_OCCURRED = "backtrack_occurred"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_ERROR = "workflow_error"
    HEARTBEAT           = "heartbeat"
    REC_TEXT_TOKEN      = "rec_text_token"
    DIRECT_ANSWER_TOKEN = "direct_answer_token"


class SSEEvent(BaseModel):
    event: EventType
    data: Dict[str, Any]

    def to_sse_string(self) -> str:
        return (
            f"event: {self.event.value}\n"
            f"data: {json.dumps(self.data, ensure_ascii=False, default=str)}\n\n"
        )
