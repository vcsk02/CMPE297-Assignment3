"""Typed inputs and outputs; deterministic validation follows model generation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Lead(StrictModel):
    company: str = Field(min_length=1, max_length=160)
    website: HttpUrl
    signals: list[str] = Field(min_length=1, max_length=8)
    citations: list[str] = Field(min_length=1, max_length=8)
    rationale: str = Field(min_length=10, max_length=1500)


class LeadReport(StrictModel):
    market: str
    patterns: list[str]
    leads: list[Lead] = Field(max_length=10)
    limitations: list[str]


class ReviewNarrative(StrictModel):
    summary: str
    recommendations: list[str]


class AgentRequest(StrictModel):
    prompt: str = Field(min_length=1, max_length=6000)
    target: str = Field(default="review_target", max_length=200)


class DeliveryUpdate(StrictModel):
    delivery: Literal["pickup", "standard", "express"]
    expected_version: int = Field(ge=1)
