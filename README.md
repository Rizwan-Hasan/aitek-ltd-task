# Open WebUI + local image generation tool (FastAPI / OpenAPI) — CPU only

Everything runs on your machine — no cloud APIs, no external API keys, and no GPU needed.

```
 browser ──► Open WebUI :3000 ──► Ollama (local LLM, CPU)
                  │
                  └─ OpenAPI tool call (Bearer key, docker network)
                        ▼
                  image-tool (FastAPI) :8001 ──► Stable Diffusion (sd-turbo, CPU)
```

| Service       | What it is                                             | Port (localhost only) |
|---------------|--------------------------------------------------------|-----------------------|
| `open-webui`  | Chat UI                                                | 3000                  |
| `ollama`      | Local LLM that decides when to call the tool           | – (internal)          |
| `image-tool`  | FastAPI OpenAPI tool server wrapping Stable Diffusion  | 8001                  |

## Requirements

- Linux with Docker + Docker Compose v2
- 16 GB RAM recommended (8 GB minimum), a modern multi-core CPU
- ~10 GB free disk (images, `sd-turbo` ≈ 2 GB, LLM ≈ 2 GB)

CPU inference is slower than a GPU: expect roughly 20–90 seconds per 512×512 image
with `sd-turbo` (4 steps), depending on your CPU, and a few tokens per second from the LLM. Models of 3B parameters or less (e.g. `llama3.2:3b`)
are too unreliable at tool calling; use 7B (`qwen2.5:7b`) or `llama3.1:8b`.

## Run it

```bash
./scripts/setup.sh                 # creates .env with freshly generated secrets
docker compose up -d --build       # first build downloads PyTorch (CPU wheel)
docker compose exec ollama ollama pull qwen2.5:7b   # reliable tool calling (needs ~5 GB RAM)
```

Open <http://localhost:3000>, create the admin account (first sign-up becomes admin), then:

1. Pick `qwen2.5:7b` as the model.
2. Open the model's **Advanced Params** (chat controls or Admin → Settings → Models) and set
   **Function Calling → Legacy**. This is required: in *Default* mode the tool call can be
   printed as text instead of executed.
3. Click **+** in the message box and make sure **Local Image Generator** is enabled.
4. Ask: *"Draw a watercolor fox in a snowy forest."*

The first image takes a few minutes (the model downloads once into the `hf-cache` volume
and is loaded into RAM); later images are faster. Smaller images are much faster
on CPU: ask for 256×256 or 384×384 if 512×512 is too slow.

Stop with `docker compose down` (add `-v` to also delete all data and models).

## How the tool is connected

- The tool server (`tool-server/app/main.py`) exposes `POST /generate_image` and
  publishes its schema at `/openapi.json`. Field descriptions and the `operationId`
  are written for the LLM.
- `docker-compose.yml` sets Open WebUI's `TOOL_SERVER_CONNECTIONS` so the server is
  registered automatically (**Admin Settings → External Tools**). Open WebUI calls
  `http://image-tool:8000` server-side over the private compose network.
- **Manual alternative:** Admin Settings → External Tools → **+**, Type *OpenAPI*,
  URL `http://image-tool:8000`, Path `openapi.json`, Auth *Bearer*, Key = the
  `TOOL_API_KEY` from `.env`.
- The tool returns an image URL plus a ready-made markdown snippet, which the model
  includes in its reply so the image renders in chat.

## Authorization and secrets

- **Bearer API key**: `/generate_image` rejects requests without
  `Authorization: Bearer <TOOL_API_KEY>` (401). Compared in constant time.
  The server refuses to start if the key is unset.
- `scripts/setup.sh` generates `TOOL_API_KEY` and `WEBUI_SECRET_KEY` with
  `openssl rand`, writes them to `.env` (mode 600). `.env` is git-ignored; only
  `.env.example` with placeholders is committed. Never put real keys in compose.
- All ports are bound to `127.0.0.1`. Ollama is not published at all. The tool
  container runs as a non-root user.
- **Images**: browsers can't send the bearer key, so `GET /images/<name>` is open,
  but file names are random 128-bit tokens (unguessable, path-traversal-safe) and
  only the 200 newest images are kept.
- To expose Open WebUI beyond localhost, put a TLS reverse proxy in front of it and
  set `PUBLIC_BASE_URL` to the externally reachable tool-server URL.

### Rotating the key

`TOOL_SERVER_CONNECTIONS` is stored by Open WebUI after first boot, so editing `.env`
later does not update it. After changing `TOOL_API_KEY`, either update the key in
Admin Settings → External Tools, or reset with `docker compose down -v` (deletes data).

## Configuration (`.env`)

| Variable              | Default                  | Meaning                                              |
|-----------------------|--------------------------|------------------------------------------------------|
| `TOOL_API_KEY`        | generated                | Bearer key for the tool server                       |
| `WEBUI_SECRET_KEY`    | generated                | Open WebUI session signing key                       |
| `PUBLIC_BASE_URL`     | `http://localhost:8001`  | URL the browser uses to load images                  |
| `MODEL_ID`            | `stabilityai/sd-turbo`   | Any Hugging Face text-to-image diffusers model       |
| `DEFAULT_STEPS`       | `4`                      | Inference steps (fewer = faster)                     |
| `GUIDANCE_SCALE`      | `0.0`                    | 0 for turbo models                                   |
| `IDLE_UNLOAD_SECONDS` | `120`                    | Unload SD from RAM after idling (0 = never)          |

`sd-turbo` is the right default for CPU because it needs only 1–4 steps. Other models
(e.g. Stable Diffusion 1.5 with 25 steps and `GUIDANCE_SCALE=7.5`) work but are
many times slower on CPU. The Ollama model unloads after 2 minutes and SD after
`IDLE_UNLOAD_SECONDS`, which keeps peak RAM lower.

## Develop / test

```bash
cd tool-server
python -m venv .venv && . .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt pytest httpx
pytest            # uses a fake generator: no model download needed
```

```
tool-server/app/
  main.py        FastAPI routes, OpenAPI metadata
  auth.py        Bearer-key dependency
  config.py      Environment-based settings
  generator.py   Lazy-loading Stable Diffusion wrapper (diffusers, CPU)
  storage.py     Random-name PNG storage + pruning
  schemas.py     Request/response models
tool-server/tests/test_api.py
```

## Troubleshooting

- *Chat shows raw JSON like `{"type":"function","name":"generate_image",...}` instead of an image*:
  the model printed the tool call as text rather than making it. Set **Function Calling → Native**
  for the model, use a 7B+ model (`qwen2.5:7b`), and start a new chat. If the image was generated
  but not displayed, the model didn't copy the `markdown` field into its reply; ask it
  "show the image" or retry. Open `http://localhost:8001/images/<name>` to view any generated file;
  `docker compose logs image-tool` shows requests.
- *Image generation is slow*: use smaller sizes (256–384 px), keep `DEFAULT_STEPS` at 1–4, close other heavy apps.
- *Model doesn't call the tool*: confirm Function Calling is **Native** and the tool is toggled on in the chat.
- *Image shows as broken*: `PUBLIC_BASE_URL` must be reachable from your browser.
- *Out of memory / container killed*: lower `IDLE_UNLOAD_SECONDS`, use a smaller LLM, or keep images small.
