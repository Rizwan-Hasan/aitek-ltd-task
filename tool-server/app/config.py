"""Runtime configuration, read from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # Bearer token clients must present. Required: the server refuses to start without it.
    tool_api_key: SecretStr

    # Base URL the *browser* uses to load generated images (JSON mode / /images route).
    public_base_url: str = "http://localhost:8001"

    # How /generate_image answers:
    #   embed - HTML the chat UI renders as an inline image (default, most reliable)
    #   json  - structured JSON with a markdown snippet the LLM must repeat
    result_mode: Literal["embed", "json"] = "embed"

    # Local Stable Diffusion model (downloaded once from Hugging Face, then cached).
    model_id: str = "stabilityai/sd-turbo"
    default_steps: int = 4
    guidance_scale: float = 0.0

    # Free RAM for the LLM after this many idle seconds (0 = never unload).
    idle_unload_seconds: int = 120

    image_dir: Path = Path("/data/images")
    max_stored_images: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
