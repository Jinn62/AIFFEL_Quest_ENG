"""FastAPI application for the translation service."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status

from app.auth import AuthenticatedUser, verify_google_user
from app.config import get_settings
from app.model_service import Translator, load_translator, timed_translation
from app.schemas import HealthResponse, TranslationRequest, TranslationResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model once at startup and share it across requests."""

    app.state.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="translator")
    app.state.translator = load_translator(get_settings())
    yield
    app.state.executor.shutdown(wait=False, cancel_futures=True)


app = FastAPI(
    title="Translation Service API",
    version="0.1.0",
    lifespan=lifespan,
)


def get_translator(request: Request) -> Translator:
    return request.app.state.translator


@app.get("/health", response_model=HealthResponse)
async def health_check(translator: Translator = Depends(get_translator)) -> HealthResponse:
    return HealthResponse(
        status="healthy",
        model_loaded=True,
        model_id=translator.model_id,
    )


@app.post(
    "/predict",
    response_model=TranslationResponse,
)
async def predict_translation(
    payload: TranslationRequest,
    request: Request,
    user: AuthenticatedUser = Depends(verify_google_user),
    translator: Translator = Depends(get_translator),
) -> TranslationResponse:
    """Validate, authenticate, and execute blocking model inference off the event loop."""

    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            request.app.state.executor,
            timed_translation,
            translator,
            payload.text,
            payload.source_language,
            payload.target_language,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Translation inference failed.",
        ) from error
