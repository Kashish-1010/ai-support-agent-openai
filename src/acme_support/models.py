from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Finding(StrictModel):
    text: str
    source_ids: list[str]


class ActionSuggestion(StrictModel):
    new_limit: int
    expected_version: int
    reason: str
    source_ids: list[str]


class Analysis(StrictModel):
    summary: Finding
    root_cause: Finding
    confidence: Literal['high', 'medium', 'insufficient']
    recommendations: list[Finding]
    uncertainties: list[str]
    proposed_action: ActionSuggestion | None


class Window(StrictModel):
    lookback_hours: int = Field(ge=1, le=168)


class NoArgs(StrictModel):
    pass
