"""Prototype 1 API contracts.

Lyric line indexes are zero-based, unique, and contiguous.
A line may carry startSeconds. Other timing fields are rejected.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TIMING_FIELDS = {
    "activeLine",
    "cue",
    "end",
    "endTime",
    "offset",
    "start",
    "startTime",
    "timestamp",
    "timestamps",
    "timing",
}

SongStatus = Literal["draft", "published"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def reject_timing_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            found = sorted(TIMING_FIELDS.intersection(data))
            if found:
                raise ValueError(f"timing fields are not allowed: {', '.join(found)}")
        return data


class ErrorDetail(ContractModel):
    field: str | None = None
    file: str | None = None
    line: int | None = Field(default=None, ge=1)


class ErrorResponse(ContractModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: list[ErrorDetail] | None = None
    requestId: str | None = None


class SongSummary(ContractModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    artist: str = Field(min_length=1)
    sourceLanguage: str = Field(min_length=1)
    targetLanguage: str = Field(min_length=1)
    durationSeconds: float | None = Field(default=None, ge=0)
    status: SongStatus


class LyricLine(ContractModel):
    id: str = Field(min_length=1)
    index: int = Field(ge=0)
    originalText: str = Field(min_length=1)
    pronunciationRomaji: str = Field(min_length=1)
    translationEnglish: str = Field(min_length=1)
    startSeconds: float | None = Field(default=None, ge=0, le=6 * 60 * 60, allow_inf_nan=False)


class LineTimeUpdate(ContractModel):
    index: int = Field(ge=0)
    startSeconds: float = Field(ge=0, le=6 * 60 * 60, allow_inf_nan=False)


class LineTimeRequest(ContractModel):
    lines: list[LineTimeUpdate] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_indexes(self) -> "LineTimeRequest":
        indexes = [line.index for line in self.lines]
        if len(indexes) != len(set(indexes)):
            raise ValueError("line indexes must be unique")
        return self


class SongDetail(SongSummary):
    audioUrl: str = Field(min_length=1)
    contentVersion: str = Field(min_length=1)
    lines: list[LyricLine]

    @model_validator(mode="after")
    def validate_line_indexes(self) -> "SongDetail":
        indexes = [line.index for line in self.lines]
        expected = list(range(len(indexes)))
        if indexes != expected:
            raise ValueError("line indexes must be zero-based, unique, and contiguous")
        return self
