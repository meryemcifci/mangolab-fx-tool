from datetime import date
from decimal import Decimal

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.errors import FXError
from app.schemas import ConversionResponse
from app.services.fx_service import FXService


app = FastAPI(
    title="MangoLab FX Tool",
    description="Foreign exchange conversion API",
    version="1.0.0",
)


@app.exception_handler(FXError)
async def fx_error_handler(
    request: Request,
    exc: FXError,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error,
            "message": exc.message,
        },
    )
    
@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": jsonable_encoder(exc.errors()),
        },
    )


fx_service = FXService()


@app.get(
    "/tools/convert",
    response_model=ConversionResponse,
)
async def convert(
    amount: Decimal = Query(...),
    from_currency: str = Query(..., alias="from"),
    to: str = Query(...),
    date: date | None = Query(default=None),
):
    return await fx_service.convert(
        amount=amount,
        from_currency=from_currency,
        to_currency=to,
        asked_date=date,
    )
