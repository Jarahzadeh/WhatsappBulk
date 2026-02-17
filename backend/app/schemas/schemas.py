from datetime import datetime

from pydantic import BaseModel, Field


class ContactIn(BaseModel):
    name: str | None = None
    phone: str
    language: str = "en"
    tags: list[str] = Field(default_factory=list)
    opt_in_status: bool = False
    opt_in_source: str | None = None
    opt_in_time: datetime | None = None
    opt_in_text: str | None = None


class CampaignCreate(BaseModel):
    name: str
    segment_query: dict
    template_name: str
    variables_json: dict = Field(default_factory=dict)
    dry_run: bool = True
    scheduled_at: datetime | None = None


class TemplateDraft(BaseModel):
    name: str
    language: str = "en"
    category: str = "marketing"
    body_draft: str


class OptOutImport(BaseModel):
    phones: list[str]
    reason: str = "imported list"


class PauseResumeRequest(BaseModel):
    status: str
