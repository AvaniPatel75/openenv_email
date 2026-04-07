from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class Urgency(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class Category(str, Enum):
    billing = "billing"
    technical = "technical"
    general = "general"
    complaint = "complaint"
    praise = "praise"

class Department(str, Enum):
    billing = "billing"
    engineering = "engineering"
    sales = "sales"
    support = "support"
    escalation = "escalation"

class EmailAction(BaseModel):
    urgency: Optional[Urgency] = None
    category: Optional[Category] = None
    department: Optional[Department] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    requires_escalation: Optional[bool] = None
    draft_reply: Optional[str] = Field(None, max_length=1000)

class EmailObservation(BaseModel):
    task: str
    current_email: Optional[dict] = None
    queue_status: Optional[List[str]] = None
    feedback: str = ""
    step_count: int = 0
    max_steps: int = 0
    done: bool = False

class EmailState(BaseModel):
    episode_id: str
    task: str
    step_count: int
    done: bool

class StepResult(BaseModel):
    observation: EmailObservation
    reward: float
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)
