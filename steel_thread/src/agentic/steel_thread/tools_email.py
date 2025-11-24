from __future__ import annotations

import json
from pathlib import Path
from typing import List

from pydantic import BaseModel

from agentic.core.tools import Tool, ToolMetadata
from .models import Email


class ListInboxInput(BaseModel):
    only_unread: bool = True


class ListInboxOutput(BaseModel):
    emails: List[Email]


class SendEmailInput(BaseModel):
    to_address: str
    subject: str
    body: str
    in_reply_to_id: str | None = None


class SendEmailOutput(BaseModel):
    sent_id: str
    message: str


class _EmailStore:
    """Tiny JSON-backed mailbox used by the demo tools."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"emails": [], "sent": []}, indent=2), encoding="utf-8")

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list_inbox(self, only_unread: bool = True) -> List[Email]:
        data = self._load()
        emails = [Email(**e) for e in data.get("emails", [])]
        if only_unread:
            emails = [e for e in emails if e.is_unread]
        emails.sort(key=lambda e: ("action_required" not in e.tags, e.subject))
        return emails

    def send_email(self, to_address: str, subject: str, body: str, in_reply_to_id: str | None) -> str:
        data = self._load()
        sent = data.setdefault("sent", [])
        new_id = f"sent-{len(sent) + 1}"
        sent.append(
            {
                "id": new_id,
                "from_address": "you@example.com",
                "to_address": to_address,
                "subject": subject,
                "body": body,
                "folder": "sent",
                "is_unread": False,
                "tags": ["outgoing"],
                "in_reply_to_id": in_reply_to_id,
            }
        )
        self._save(data)
        return new_id


def build_email_tools(mailbox_path: Path) -> list[Tool]:
    store = _EmailStore(mailbox_path)

    def list_inbox_func(inp: ListInboxInput) -> ListInboxOutput:
        emails = store.list_inbox(only_unread=inp.only_unread)
        return ListInboxOutput(emails=emails)

    def send_email_func(inp: SendEmailInput) -> SendEmailOutput:
        sent_id = store.send_email(
            to_address=inp.to_address,
            subject=inp.subject,
            body=inp.body,
            in_reply_to_id=inp.in_reply_to_id,
        )
        return SendEmailOutput(
            sent_id=sent_id,
            message=f"Queued email {sent_id} to {inp.to_address}",
        )

    list_inbox_tool = Tool[ListInboxInput, ListInboxOutput](
        metadata=ToolMetadata(
            name="list_inbox",
            description="List emails in the inbox, prioritising action-required messages.",
            is_write=False,
            dangerous=False,
        ),
        input_model=ListInboxInput,
        output_model=ListInboxOutput,
        func=list_inbox_func,
    )

    send_email_tool = Tool[SendEmailInput, SendEmailOutput](
        metadata=ToolMetadata(
            name="send_email",
            description="Send an email reply. This is side-effecting and requires human approval.",
            is_write=True,
            dangerous=True,
        ),
        input_model=SendEmailInput,
        output_model=SendEmailOutput,
        func=send_email_func,
    )

    return [list_inbox_tool, send_email_tool]
