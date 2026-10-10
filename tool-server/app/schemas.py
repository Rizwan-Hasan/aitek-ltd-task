"""Request/response models. Field descriptions are what the LLM reads.

Kept deliberately small: small local LLMs call tools much more reliably when
the schema has one required argument and few optional ones.
"""

from pydantic import BaseModel, Field


class GenerateImageRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Description of the image to draw, in English, e.g. 'a watercolor fox in a snowy forest'.",
    )
    width: int = Field(default=512, ge=256, le=768, multiple_of=8, description="Width in pixels (default 512).")
    height: int = Field(default=512, ge=256, le=768, multiple_of=8, description="Height in pixels (default 512).")


class GenerateImageResponse(BaseModel):
    image_url: str = Field(description="URL of the generated PNG.")
    markdown: str = Field(
        description="Markdown that displays the image. Copy it exactly into your reply to the user."
    )
    width: int
    height: int
