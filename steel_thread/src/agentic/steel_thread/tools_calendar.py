from __future__ import annotations

import json
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import List

from pydantic import BaseModel

from agentic.core.tools import Tool, ToolMetadata
from .models import CalendarEvent, TimeSlot


class FindFreeSlotsInput(BaseModel):
    duration_minutes: int = 30
    days_ahead: int = 7
    num_options: int = 1


class FindFreeSlotsOutput(BaseModel):
    slots: List[TimeSlot]


class CreateEventInput(BaseModel):
    title: str
    participants: List[str]
    start: datetime
    end: datetime
    location: str = "Zoom"


class CreateEventOutput(BaseModel):
    event_id: str


class _CalendarStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"events": []}, indent=2), encoding="utf-8")

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list_events(self) -> List[CalendarEvent]:
        data = self._load()
        events_raw = data.get("events", [])
        events: List[CalendarEvent] = []
        for e in events_raw:
            events.append(
                CalendarEvent(
                    id=e["id"],
                    title=e["title"],
                    participants=e["participants"],
                    start=datetime.fromisoformat(e["start"]),
                    end=datetime.fromisoformat(e["end"]),
                    location=e["location"],
                )
            )
        return events

    def add_event(self, event: CalendarEvent) -> str:
        data = self._load()
        events = data.setdefault("events", [])
        events.append(
            {
                "id": event.id,
                "title": event.title,
                "participants": event.participants,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "location": event.location,
            }
        )
        self._save(data)
        return event.id


def _find_free_slots(store: _CalendarStore, inp: FindFreeSlotsInput) -> List[TimeSlot]:
    """Very small free/busy search with naive working hours (09:00–17:00)."""
    events = store.list_events()
    events_by_day: dict[str, List[CalendarEvent]] = {}
    for e in events:
        key = e.start.date().isoformat()
        events_by_day.setdefault(key, []).append(e)

    today = datetime.utcnow().date()
    duration = timedelta(minutes=inp.duration_minutes)
    slots: List[TimeSlot] = []

    for offset in range(1, inp.days_ahead + 1):
        day = today + timedelta(days=offset)
        day_str = day.isoformat()
        busy = events_by_day.get(day_str, [])
        start_dt = datetime.combine(day, time(9, 0))
        end_of_day = datetime.combine(day, time(17, 0))

        while start_dt + duration <= end_of_day:
            candidate_end = start_dt + duration

            def overlaps(ev: CalendarEvent) -> bool:
                return not (candidate_end <= ev.start or start_dt >= ev.end)

            if not any(overlaps(ev) for ev in busy):
                slots.append(TimeSlot(start=start_dt, end=candidate_end))
                if len(slots) >= inp.num_options:
                    return slots

            start_dt += timedelta(minutes=30)

    return slots


def build_calendar_tools(calendar_path: Path) -> list[Tool]:
    store = _CalendarStore(calendar_path)

    def find_slots_func(inp: FindFreeSlotsInput) -> FindFreeSlotsOutput:
        slots = _find_free_slots(store, inp)
        return FindFreeSlotsOutput(slots=slots)

    def create_event_func(inp: CreateEventInput) -> CreateEventOutput:
        new_id = f"event-{len(store.list_events()) + 1}"
        event = CalendarEvent(
            id=new_id,
            title=inp.title,
            participants=inp.participants,
            start=inp.start,
            end=inp.end,
            location=inp.location,
        )
        store.add_event(event)
        return CreateEventOutput(event_id=new_id)

    find_slots_tool = Tool[FindFreeSlotsInput, FindFreeSlotsOutput](
        metadata=ToolMetadata(
            name="find_free_slots",
            description="Find upcoming free calendar slots for the primary user.",
            is_write=False,
            dangerous=False,
        ),
        input_model=FindFreeSlotsInput,
        output_model=FindFreeSlotsOutput,
        func=find_slots_func,
    )

    create_event_tool = Tool[CreateEventInput, CreateEventOutput](
        metadata=ToolMetadata(
            name="create_event",
            description="Create a calendar event (side-effecting, requires approval).",
            is_write=True,
            dangerous=True,
        ),
        input_model=CreateEventInput,
        output_model=CreateEventOutput,
        func=create_event_func,
    )

    return [find_slots_tool, create_event_tool]
