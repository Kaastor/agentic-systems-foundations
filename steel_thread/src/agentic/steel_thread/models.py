from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel


class Email(BaseModel):
    id: str
    from_address: str
    to_address: str
    subject: str
    body: str
    folder: str = "inbox"
    is_unread: bool = True
    tags: List[str] = []


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
