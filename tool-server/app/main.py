"""FastAPI OpenAPI tool server: local image generation for Open WebUI."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .auth import require_api_key
from .config import Settings, get_settings
from .generator import DiffusersGenerator, ImageGenerator
from .schemas import GenerateImageRequest, GenerateImageResponse
from .storage import is_valid_name, save_image


def get_generator(request: Request) -> ImageGenerator:
    return request.app.state.generator


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "generator"):
        app.state.generator = DiffusersGenerator(get_settings())
    app.state.generator.start()
    yield
    app.state.generator.stop()


app = FastAPI(
    title="Local Image Generator",
    version="1.0.0",
    description="Generates images from text prompts with a Stable Diffusion model running locally on the CPU.",
    lifespan=lifespan,
)

# Open WebUI fetches the spec server-side; CORS is only needed if a browser calls it directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/generate_image",
    operation_id="generate_image",
    summary="Generate an image from a text prompt",
    description=(
        "Draw or generate an image, picture, illustration or artwork. Call with a `prompt` string "
        "describing the image. Returns a `markdown` field; copy it exactly into your reply so the user sees the image."
    ),
    response_model=GenerateImageResponse,
    dependencies=[Depends(require_api_key)],
)
async def generate_image(
    body: GenerateImageRequest,
    generator: ImageGenerator = Depends(get_generator),
    settings: Settings = Depends(get_settings),
) -> GenerateImageResponse:
    try:
        image, _seed = await run_in_threadpool(
            generator.generate,
            body.prompt,
            None,  # negative_prompt: not exposed to the LLM (sd-turbo ignores it anyway)
            body.width,
            body.height,
            None,  # steps: use DEFAULT_STEPS
            None,  # seed: random
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    name = await run_in_threadpool(save_image, image, settings.image_dir, settings.max_stored_images)
    url = f"{settings.public_base_url.rstrip('/')}/images/{name}"
    alt = body.prompt[:80].replace("[", "(").replace("]", ")").replace("\n", " ")
    return GenerateImageResponse(
        image_url=url,
        markdown=f"![{alt}]({url})",
        width=body.width,
        height=body.height,
    )


@app.get("/images/{name}", include_in_schema=False)
def get_image(name: str, settings: Settings = Depends(get_settings)) -> FileResponse:
    """Serve a generated image. Names are random 128-bit tokens, so only
    someone who was handed the URL can fetch it (browsers can't send the bearer key)."""
    if not is_valid_name(name):
        raise HTTPException(status_code=404)
    path = settings.image_dir / name
    if not path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "private, max-age=86400"})
