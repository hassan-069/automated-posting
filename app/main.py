"""FastAPI entrypoint: POST /posting"""
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.platforms import build_platforms
from app.schemas import PostingRequest, PostingResponse, ValidationErrorResponse
from app.services.posting_service import PostingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = httpx.AsyncClient(
        timeout=settings.request_timeout,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AutomatedPostingBot/1.0)"},
    )
    app.state.service = PostingService(
        build_platforms(settings, client), client, platform_timeout=settings.platform_timeout
    )
    yield
    await client.aclose()


app = FastAPI(
    title="Automated Multi-Platform Posting",
    description="Publishes a short message with one CTA link to several third-party platforms.",
    version="1.0.0",
    lifespan=lifespan,
)


def get_service(request: Request) -> PostingService:
    return request.app.state.service


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(p) for p in err["loc"] if p != "body") or "body",
            "message": err["msg"].removeprefix("Value error, "),
        }
        for err in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"success": False, "errors": errors})


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/posting",
    response_model=PostingResponse,
    responses={422: {"model": ValidationErrorResponse, "description": "Invalid message"}},
    tags=["posting"],
    summary="Publish a message to all configured platforms",
)
async def create_posting(
    payload: PostingRequest, service: PostingService = Depends(get_service)
) -> PostingResponse:
    results = await service.publish_all(payload.message)
    return PostingResponse(success=any(r.status == "success" for r in results), results=results)
