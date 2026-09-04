from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.errors import FXError
from app.services.fx_service import FXService


class MockTransport:
    def __init__(self, response_data):
        self.response_data = response_data
        self.request_count = 0

    async def handle_request(self, request):
        self.request_count += 1

        return httpx.Response(
            status_code=200,
            json=self.response_data,
            request=request,
        )


@pytest.mark.asyncio
async def test_convert_success(fx_service):
    transport = MockTransport(
        {
            "amount": 1,
            "base": "USD",
            "date": "2026-09-03",
            "rates": {
                "EUR": 0.86096,
            },
        }
    )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport.handle_request)
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        response = await service.convert(
            amount=Decimal("100"),
            from_currency="USD",
            to_currency="EUR",
        )

    assert response.amount == Decimal("100")
    assert response.from_ == "USD"
    assert response.to == "EUR"
    assert response.rate == Decimal("0.86096")
    assert response.result == Decimal("86.09600")
    assert response.rate_date == "2026-09-03"
    assert response.source == "frankfurter"


@pytest.mark.asyncio
async def test_same_currency(fx_service):
    response = await fx_service.convert(
        amount=Decimal("100"),
        from_currency="USD",
        to_currency="USD",
    )

    assert response.amount == Decimal("100")
    assert response.from_ == "USD"
    assert response.to == "USD"
    assert response.rate == Decimal("1")
    assert response.result == Decimal("100")
    assert response.source == "same_currency"


@pytest.mark.asyncio
async def test_invalid_amount(fx_service):
    with pytest.raises(FXError) as exc_info:
        await fx_service.convert(
            amount=Decimal("0"),
            from_currency="USD",
            to_currency="EUR",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error == "INVALID_AMOUNT"


@pytest.mark.asyncio
async def test_negative_amount(fx_service):
    with pytest.raises(FXError) as exc_info:
        await fx_service.convert(
            amount=Decimal("-10"),
            from_currency="USD",
            to_currency="EUR",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error == "INVALID_AMOUNT"


@pytest.mark.asyncio
async def test_invalid_currency(fx_service):
    with pytest.raises(FXError) as exc_info:
        await fx_service.convert(
            amount=Decimal("100"),
            from_currency="US",
            to_currency="EUR",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error == "INVALID_CURRENCY"


@pytest.mark.asyncio
async def test_currency_is_normalized(fx_service):
    transport = MockTransport(
        {
            "amount": 1,
            "base": "USD",
            "date": "2026-09-03",
            "rates": {
                "EUR": 0.86096,
            },
        }
    )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport.handle_request)
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        response = await service.convert(
            amount=Decimal("100"),
            from_currency=" usd ",
            to_currency=" eur ",
        )

    assert response.from_ == "USD"
    assert response.to == "EUR"


@pytest.mark.asyncio
async def test_cache_is_used(fx_service):
    transport = MockTransport(
        {
            "amount": 1,
            "base": "USD",
            "date": "2026-09-03",
            "rates": {
                "EUR": 0.86096,
            },
        }
    )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport.handle_request)
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        first_response = await service.convert(
            amount=Decimal("100"),
            from_currency="USD",
            to_currency="EUR",
        )

        second_response = await service.convert(
            amount=Decimal("200"),
            from_currency="USD",
            to_currency="EUR",
        )

    assert first_response.source == "frankfurter"
    assert second_response.source == "cache"

    assert first_response.rate == second_response.rate

    assert transport.request_count == 1


@pytest.mark.asyncio
async def test_specific_date(fx_service):
    transport = MockTransport(
        {
            "amount": 1,
            "base": "USD",
            "date": "2026-08-28",
            "rates": {
                "EUR": 0.85500,
            },
        }
    )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport.handle_request
        )
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        response = await service.convert(
            amount=Decimal("100"),
            from_currency="USD",
            to_currency="EUR",
            asked_date=date(2026, 8, 28),
        )

    assert response.asked_date == "2026-08-28"
    assert response.rate_date == "2026-08-28"
    assert response.rate == Decimal("0.85500")
    
@pytest.mark.asyncio
async def test_rate_date_can_differ_from_asked_date(fx_service):
    transport = MockTransport(
        {
            "amount": 1,
            "base": "USD",
            "date": "2026-08-27",
            "rates": {
                "EUR": 0.85500,
            },
        }
    )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport.handle_request)
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        response = await service.convert(
            amount=Decimal("100"),
            from_currency="USD",
            to_currency="EUR",
            asked_date=date(2026, 8, 28),
        )

    assert response.asked_date == "2026-08-28"
    assert response.rate_date == "2026-08-27"
    assert response.rate == Decimal("0.85500")
    assert response.result == Decimal("85.50000")    
    
@pytest.mark.asyncio
async def test_upstream_500(fx_service):
    async def handle_request(request):
        return httpx.Response(
            status_code=500,
            json={"error": "internal server error"},
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        with pytest.raises(FXError) as exc_info:
            await service.convert(
                amount=Decimal("100"),
                from_currency="USD",
                to_currency="EUR",
            )

    assert exc_info.value.status_code == 502
    assert exc_info.value.error == "UPSTREAM_ERROR"


@pytest.mark.asyncio
async def test_upstream_timeout(fx_service):
    async def handle_request(request):
        raise httpx.ReadTimeout(
            "Upstream timed out",
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        with pytest.raises(FXError) as exc_info:
            await service.convert(
                amount=Decimal("100"),
                from_currency="USD",
                to_currency="EUR",
            )

    assert exc_info.value.status_code == 504
    assert exc_info.value.error == "UPSTREAM_TIMEOUT"


@pytest.mark.asyncio
async def test_invalid_upstream_json(fx_service):
    async def handle_request(request):
        return httpx.Response(
            status_code=200,
            content=b"this is not json",
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        with pytest.raises(FXError) as exc_info:
            await service.convert(
                amount=Decimal("100"),
                from_currency="USD",
                to_currency="EUR",
            )

    assert exc_info.value.status_code == 502
    assert exc_info.value.error == "INVALID_UPSTREAM_RESPONSE"


@pytest.mark.asyncio
async def test_missing_rate_in_upstream_response(fx_service):
    async def handle_request(request):
        return httpx.Response(
            status_code=200,
            json={
                "amount": 1,
                "base": "USD",
                "date": "2026-09-03",
                "rates": {},
            },
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        with pytest.raises(FXError) as exc_info:
            await service.convert(
                amount=Decimal("100"),
                from_currency="USD",
                to_currency="EUR",
            )

    assert exc_info.value.status_code == 502
    assert exc_info.value.error == "INVALID_UPSTREAM_RESPONSE"
    
@pytest.mark.asyncio
async def test_future_date_returns_rate_not_found(fx_service):
    async def handle_request(request):
        return httpx.Response(
            status_code=404,
            json={
                "message": "No rates available for this date."
            },
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        with pytest.raises(FXError) as exc_info:
            await service.convert(
                amount=Decimal("100"),
                from_currency="USD",
                to_currency="EUR",
                asked_date=date(2099, 1, 1),
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.error == "RATE_NOT_FOUND"
    
@pytest.mark.asyncio
async def test_date_before_series_start_returns_rate_not_found(fx_service):
    async def handle_request(request):
        return httpx.Response(
            status_code=404,
            json={
                "message": "No rates available for this date."
            },
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        with pytest.raises(FXError) as exc_info:
            await service.convert(
                amount=Decimal("100"),
                from_currency="USD",
                to_currency="EUR",
                asked_date=date(1900, 1, 1),
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.error == "RATE_NOT_FOUND"


@pytest.mark.asyncio
async def test_previous_published_rate_is_visible(fx_service):
    async def handle_request(request):
        return httpx.Response(
            status_code=200,
            json={
                "amount": 1,
                "base": "USD",
                "date": "2026-08-27",
                "rates": {
                    "EUR": 0.85500,
                },
            },
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        response = await service.convert(
            amount=Decimal("100"),
            from_currency="USD",
            to_currency="EUR",
            asked_date=date(2026, 8, 28),
        )

    assert response.asked_date == "2026-08-28"
    assert response.rate_date == "2026-08-27"
    assert response.rate == Decimal("0.85500")
    assert response.result == Decimal("85.50000")
    
@pytest.mark.asyncio
async def test_amount_with_ten_decimal_places_is_accepted(fx_service):
    transport = MockTransport(
        {
            "amount": 1,
            "base": "USD",
            "date": "2026-09-03",
            "rates": {
                "EUR": 0.86096,
            },
        }
    )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport.handle_request)
    ) as client:

        service = FXService(
            cache=fx_service.cache,
            client=client,
        )

        response = await service.convert(
            amount=Decimal("100.1234567890"),
            from_currency="USD",
            to_currency="EUR",
        )

    assert response.amount == Decimal("100.1234567890")
    assert response.rate == Decimal("0.86096")
    
@pytest.mark.asyncio
async def test_amount_with_more_than_ten_decimal_places_is_rejected(fx_service):
    with pytest.raises(FXError) as exc_info:
        await fx_service.convert(
            amount=Decimal("100.12345678901"),
            from_currency="USD",
            to_currency="EUR",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error == "INVALID_AMOUNT"