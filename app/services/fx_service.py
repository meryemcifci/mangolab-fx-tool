# Upstream Frankfurter API ile konuşacak ve conversion işini burada tutacağım.

from datetime import date
from decimal import Decimal, InvalidOperation

import httpx

from app.cache import TTLCache
from app.config import UPSTREAM_BASE_URL
from app.errors import FXError
from app.schemas import ConversionResponse


class FXService:
    def __init__(
        self,
        cache: TTLCache | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.cache = cache or TTLCache()
        self.client = client

    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        asked_date: date | None = None,
    ) -> ConversionResponse:

        from_currency = from_currency.strip().upper()
        to_currency = to_currency.strip().upper()

        # Amount validation
        if amount <= 0:
            raise FXError(
                status_code=400,
                error="INVALID_AMOUNT",
                message="Amount must be greater than zero.",
            )
        if abs(amount.as_tuple().exponent) > 10:
            raise FXError(
                status_code=400,
                error="INVALID_AMOUNT",
                message="Amount cannot have more than 10 decimal places.",
            )    

        # Currency validation
        if (
            len(from_currency) != 3
            or not from_currency.isalpha()
            or len(to_currency) != 3
            or not to_currency.isalpha()
        ):
            raise FXError(
                status_code=400,
                error="INVALID_CURRENCY",
                message="Currency codes must be valid three-letter codes.",
            )

 
      # Same currency
        if from_currency == to_currency:

            # Currency gerçekten destekleniyor mu kontrol et.
            currencies_url = f"{UPSTREAM_BASE_URL}/v1/currencies"

            try:
                if self.client is not None:
                    currencies_response = await self.client.get(currencies_url)
                else:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        currencies_response = await client.get(currencies_url)

            except httpx.TimeoutException as exc:
                raise FXError(
                    status_code=504,
                    error="UPSTREAM_TIMEOUT",
                    message="The exchange rate service timed out.",
                ) from exc

            except httpx.RequestError as exc:
                raise FXError(
                    status_code=502,
                    error="UPSTREAM_UNAVAILABLE",
                    message="The exchange rate service is currently unavailable.",
                ) from exc

            if currencies_response.status_code != 200:
                raise FXError(
                    status_code=502,
                    error="UPSTREAM_ERROR",
                    message="The exchange rate service returned an error.",
                )

            try:
                currencies = currencies_response.json()

                if not isinstance(currencies, dict):
                    raise ValueError

            except (ValueError, TypeError):
                raise FXError(
                    status_code=502,
                    error="INVALID_UPSTREAM_RESPONSE",
                    message="The exchange rate service returned an invalid response.",
                )

            if from_currency not in currencies:
                raise FXError(
                    status_code=400,
                    error="INVALID_CURRENCY",
                    message="Unsupported currency code.",
                )

            requested_date = asked_date or date.today()

            return ConversionResponse(
                amount=amount,
                from_=from_currency,
                to=to_currency,
                rate=Decimal("1"),
                result=amount,
                rate_date=requested_date.isoformat(),
                asked_date=requested_date.isoformat(),
                source="same_currency",
            )

        requested_date = asked_date or date.today()

        cache_key = (
            f"{from_currency}-{to_currency}-{requested_date.isoformat()}"
        )

        cached_rate = self.cache.get(cache_key)

        if cached_rate is not None:
            rate, rate_date = cached_rate
            source = "cache"
        else:
            rate, rate_date = await self._get_rate(
                from_currency=from_currency,
                to_currency=to_currency,
                requested_date=requested_date,
            )

            self.cache.set(cache_key, (rate, rate_date))
            source = "frankfurter"

        result = amount * rate

        return ConversionResponse(
            amount=amount,
            from_=from_currency,
            to=to_currency,
            rate=rate,
            result=result,
            rate_date=rate_date,
            asked_date=requested_date.isoformat(),
            source=source,
        )

    async def _get_rate(
        self,
        from_currency: str,
        to_currency: str,
        requested_date: date,
    ) -> tuple[Decimal, str]:

        url = (
            f"{UPSTREAM_BASE_URL}/v1/"
            f"{requested_date.isoformat()}"
        )

        params = {
            "base": from_currency,
            "symbols": to_currency,
        }

        try:
            if self.client is not None:
                response = await self.client.get(url, params=params)
            else:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, params=params)

        except httpx.TimeoutException as exc:
            raise FXError(
                status_code=504,
                error="UPSTREAM_TIMEOUT",
                message="The exchange rate service timed out.",
            ) from exc

        except httpx.RequestError as exc:
            raise FXError(
                status_code=502,
                error="UPSTREAM_UNAVAILABLE",
                message="The exchange rate service is currently unavailable.",
            ) from exc

        if response.status_code == 404:
            currencies_url = f"{UPSTREAM_BASE_URL}/v1/currencies"

            try:
                if self.client is not None:
                    currencies_response = await self.client.get(currencies_url)
                else:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        currencies_response = await client.get(currencies_url)

            except httpx.TimeoutException as exc:
                raise FXError(
                    status_code=504,
                    error="UPSTREAM_TIMEOUT",
                    message="The exchange rate service timed out.",
                ) from exc

            except httpx.RequestError as exc:
                raise FXError(
                    status_code=502,
                    error="UPSTREAM_UNAVAILABLE",
                    message="The exchange rate service is currently unavailable.",
                ) from exc

            if currencies_response.status_code != 200:
                raise FXError(
                    status_code=404,
                    error="RATE_NOT_FOUND",
                    message="Exchange rate could not be found for the requested date.",
                )

            try:
                currencies = currencies_response.json()

                if not isinstance(currencies, dict):
                    raise ValueError

            except (ValueError, TypeError):
                raise FXError(
                    status_code=502,
                    error="INVALID_UPSTREAM_RESPONSE",
                    message="The exchange rate service returned an invalid response.",
                )

            if (
                from_currency not in currencies
                or to_currency not in currencies
            ):
                raise FXError(
                    status_code=400,
                    error="INVALID_CURRENCY",
                    message="Unsupported currency code.",
                )

            raise FXError(
                status_code=404,
                error="RATE_NOT_FOUND",
                message="Exchange rate could not be found for the requested date.",
            )

        if response.status_code != 200:
            raise FXError(
                status_code=502,
                error="UPSTREAM_ERROR",
                message="The exchange rate service returned an error.",
            )

        try:
            data = response.json()

            upstream_date = data["date"]
            rates = data["rates"]
            rate_value = rates[to_currency]

            rate = Decimal(str(rate_value))

            parsed_rate_date = date.fromisoformat(upstream_date)

        except (KeyError, TypeError, InvalidOperation, ValueError):
            raise FXError(
                status_code=502,
                error="INVALID_UPSTREAM_RESPONSE",
                message="The exchange rate service returned an invalid response.",
            )

        return rate, parsed_rate_date.isoformat()