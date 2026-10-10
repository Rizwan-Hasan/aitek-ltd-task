"""Local Stable Diffusion wrapper (CPU).

The pipeline is loaded lazily on first use and unloaded after a period of
inactivity, so the RAM is free for the LLM (Ollama) in between requests.
"""

import gc
import logging
import random
import threading
import time
from typing import Protocol

from PIL import Image

from .config import Settings

log = logging.getLogger(__name__)


class ImageGenerator(Protocol):
    """Interface the API depends on (lets tests swap in a fake)."""

    def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        width: int,
        height: int,
        steps: int | None,
        seed: int | None,
    ) -> tuple[Image.Image, int]: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...


class DiffusersGenerator:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._pipe = None
        self._lock = threading.Lock()  # one generation at a time; CPU inference is heavy
        self._last_used = time.monotonic()
        self._stop_event = threading.Event()
        self._reaper: threading.Thread | None = None

    # -- lifecycle -------------------------------------------------------
    def start(self) -> None:
        if self._settings.idle_unload_seconds > 0:
            self._reaper = threading.Thread(target=self._reap_loop, daemon=True)
            self._reaper.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            self._unload()

    # -- generation ------------------------------------------------------
    def generate(self, prompt, negative_prompt, width, height, steps, seed):
        import torch

        seed = random.randrange(2**32) if seed is None else seed
        with self._lock:
            pipe = self._load()
            generator = torch.Generator(device="cpu").manual_seed(seed)
            result = pipe(
                prompt=prompt,
                # Guidance-free models (sd-turbo) must not receive a negative prompt.
                negative_prompt=negative_prompt if self._settings.guidance_scale > 1.0 else None,
                width=width,
                height=height,
                num_inference_steps=steps or self._settings.default_steps,
                guidance_scale=self._settings.guidance_scale,
                generator=generator,
            )
            self._last_used = time.monotonic()
        return result.images[0], seed

    # -- internals -------------------------------------------------------
    def _load(self):
        if self._pipe is None:
            import torch
            from diffusers import AutoPipelineForText2Image

            log.info("Loading %s on the CPU", self._settings.model_id)
            # float32: half precision is slow or unsupported for many CPU ops.
            # The fp16 variant is only used to halve the download; it is upcast on load.
            pipe = AutoPipelineForText2Image.from_pretrained(
                self._settings.model_id, torch_dtype=torch.float32, variant="fp16"
            )
            pipe.set_progress_bar_config(disable=True)
            self._pipe = pipe
        return self._pipe

    def _unload(self) -> None:
        if self._pipe is not None:
            log.info("Unloading model to free RAM")
            self._pipe = None
            gc.collect()

    def _reap_loop(self) -> None:
        while not self._stop_event.wait(10):
            idle = time.monotonic() - self._last_used
            if idle >= self._settings.idle_unload_seconds and self._lock.acquire(blocking=False):
                try:
                    self._unload()
                finally:
                    self._lock.release()
