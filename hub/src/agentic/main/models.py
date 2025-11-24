from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class EmailTag(str, Enum):
    """Enum for email tags so we can talk about typed enums (Module 1)."""

    ACTION_REQUIRED = "action_required"
    INFO = "info"
    LOW_PRIORITY = "low_priority"
    OUTGOING = "outgoing"


class Email(BaseModel):
    id: str
    from_address: str
    to_address: str
    subject: str
    body: str
    folder: str = "inbox"
    is_unread: bool = True
    tags: List[EmailTag] = Field(default_factory=list)


class CalendarEvent(BaseModel):
    id: str
    title: str
    participants: List[str]
    start: datetime
    end: datetime
    location: str


class TimeSlot(BaseModel):
    start: datetime
    end: datetime


class DocumentHit(BaseModel):
    id: str
    title: str
    snippet: str
    score: float
    path: str
