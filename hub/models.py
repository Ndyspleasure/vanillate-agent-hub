import re
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Id = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}$")]
Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=140)]
Summary = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=600)]
Authority = Literal["USER_DECISION", "APPROVED_SPECIFICATION", "IMPLEMENTATION_PLAN",
                    "OLLAMA_OBSERVATION", "NON_BINDING_SUGGESTION", "VERIFIED_DEFECT",
                    "TECHNICAL_OBSERVATION", "NEEDS_FOUNDER_REVIEW"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    @field_validator("*", mode="before")
    @classmethod
    def metadata_only(cls, value):
        if isinstance(value, str) and re.search(
            r"(?i)(-----BEGIN .*PRIVATE KEY|\bBearer\s+|gh[pousr]_|github_pat_|sk-[a-zA-Z0-9]{12}|"
            r"(?:password|token|secret|api[_-]?key)\s*[:=]|[\x00-\x1f])", value
        ):
            raise ValueError("Expected public metadata")
        return value


class Project(Input):
    id: Id
    name: Short


class Resource(Project):
    kind: Id
    locator: Annotated[str, Field(min_length=1, max_length=350)]
    summary: Summary
    source: Annotated[str, Field(min_length=1, max_length=350)]
    authority: Authority = "TECHNICAL_OBSERVATION"

    @field_validator("locator", "source")
    @classmethod
    def safe_ref(cls, value):
        parts = urlsplit(value)
        if (parts.scheme and (parts.scheme != "https" or not parts.hostname)
                or parts.netloc and not parts.scheme or parts.username is not None
                or "?" in value or "#" in value or "\\" in value or any(c.isspace() for c in value)):
            raise ValueError("Use an HTTPS or path reference without credentials or parameters")
        return value


class Link(Input):
    origin: Id
    target: Id
    kind: Id
    evidence: Id  # registered source resource


class Event(Input):
    external_id: Id
    resource: Id
    kind: Literal["file.changed", "document.changed", "commit.changed"]
    version: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}([0-9a-f]{24})?$")]


class Result(Input):
    lease: Id
    summary: Summary
    model: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,99}$")]


class Review(Input):
    decision: Literal["accepted", "rejected"]
