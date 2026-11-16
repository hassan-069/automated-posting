"""Request / response models."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.validators import validate_message


class PostingRequest(BaseModel):
    message: str = Field(
        ...,
        description="Message to publish. Max 200 characters, exactly one http(s) CTA link.",
        examples=["Check out our latest business platform and grow your online visibility. https://example.com"],
    )

    @field_validator("message")
    @classmethod
    def _validate_message(cls, value: str) -> str:
        return validate_message(value)


class PlatformResult(BaseModel):
    platform: str
    status: Literal["success", "failed"]
    posted_url: str | None = None
    public_access: bool = False
    date: str | None = Field(None, description="UTC date, YYYY-MM-DD")
    time: str | None = Field(None, description="UTC time, HH:MM:SS")
    error: str | None = None


class PostingResponse(BaseModel):
    success: bool = Field(..., description="True if at least one platform succeeded")
    results: list[PlatformResult]


class FieldError(BaseModel):
    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    success: Literal[False] = False
    errors: list[FieldError]
