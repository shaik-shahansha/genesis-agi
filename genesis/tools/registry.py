"""Tool registry for Genesis Minds."""

from typing import Optional
from pydantic import BaseModel, Field


class Tools(BaseModel):
    """Tools configuration for a Mind."""

    # Communication
    email: list[str] = Field(default_factory=list)
    messaging: list[str] = Field(default_factory=list)
    calendar: list[str] = Field(default_factory=list)

    # Productivity
    project_management: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    # Data
    databases: list[str] = Field(default_factory=list)
    apis: list[str] = Field(default_factory=list)

    # Capabilities
    code_execution: bool = False
    web_search: bool = True
    image_generation: bool = False
