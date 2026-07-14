from pydantic import BaseModel
from datetime import datetime


class ConversationSchema(BaseModel):
    conversation_id: str
    user_id: int
    user_type: str
    active_agent: str
    status: str
    started_at: datetime
    last_interaction_at: datetime