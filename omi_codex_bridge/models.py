from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str
    speaker: str | None = "SPEAKER_00"
    speaker_id: int | None = Field(default=None, alias="speakerId")
    is_user: bool = False
    start: float = 0.0
    end: float = 0.0

    @property
    def stable_key(self) -> str:
        return f"{self.speaker}:{self.start:.2f}:{self.end:.2f}:{self.text.strip().lower()}"


class ToolBaseRequest(BaseModel):
    uid: str
    app_id: str = "omi_codex_bridge"
    tool_name: str
    geolocation: dict[str, Any] | None = None


class CheckBridgeStatusRequest(ToolBaseRequest):
    pass


class CheckPhoneStatusRequest(ToolBaseRequest):
    pass


class StartCodexTaskRequest(ToolBaseRequest):
    prompt: str
    workspace: str | None = None
    run_immediately: bool = False


class OpenDesktopFileRequest(ToolBaseRequest):
    query: str | None = None
    create_demo_if_needed: bool = True


class ShowOnAndroidRequest(ToolBaseRequest):
    title: str = "Codex"
    message: str
    expand_notifications: bool = False


class QuickCodexTaskRequest(ToolBaseRequest):
    task_type: str
    details: str
    workspace: str | None = None
    run_immediately: bool = False


class RunCodexJobRequest(ToolBaseRequest):
    job_id: str


class RunNextCodexJobRequest(ToolBaseRequest):
    status: str = "pending"


class GetCodexJobRequest(ToolBaseRequest):
    job_id: str


class ListCodexJobsRequest(ToolBaseRequest):
    status: str | None = None
    limit: int = 10


class CancelCodexJobRequest(ToolBaseRequest):
    job_id: str


class RetryCodexJobRequest(ToolBaseRequest):
    job_id: str
    run_immediately: bool = False


class GetCodexJobOutputRequest(ToolBaseRequest):
    job_id: str
    max_chars: int = 4000
