# MangoLab FX Tool

A small FastAPI service that converts currencies using exchange rates from the Frankfurter API.

## Requirements

* Python 3.10+
* FastAPI
* Uvicorn
* pytest
* httpx

## Run

Create and activate a virtual environment, then install the dependencies:

```bash
pip install -r requirements.txt
```

Start the service:

```bash
./run.sh
```

The service listens on port `8080` by default.

A different port can be provided with:

```bash
PORT=9000 ./run.sh
```

The upstream API can be configured with:

```bash
FX_UPSTREAM_BASE=http://localhost:9001 ./run.sh
```

The default upstream is:

```text
https://api.frankfurter.dev
```

The application does not hardcode the upstream host outside configuration.

## API

### Convert currency

```http
GET /tools/convert
```

Example:

```text
/tools/convert?amount=250&from=EUR&to=TRY&date=2026-08-28
```

Example response:

```json
{
  "amount": "250",
  "from": "EUR",
  "to": "TRY",
  "rate": "56.1718",
  "result": "14042.9500",
  "rate_date": "2026-08-28",
  "asked_date": "2026-08-28",
  "source": "frankfurter"
}
```

`rate_date` is the actual date of the rate returned by the upstream service.

`asked_date` is the date requested by the caller.

These dates may differ. The service never changes the upstream rate date to make it appear as though the rate belongs to the requested date.

## Behaviour

### Weekends and holidays

The ECB does not publish rates for every calendar day.

If Frankfurter cannot provide a rate for the requested date, the service returns `RATE_NOT_FOUND` rather than silently using a rate from another day.

This avoids presenting an older rate as though it belonged to the requested date.

If an upstream response explicitly contains an earlier published rate, its actual date is returned in `rate_date`, while the requested date remains in `asked_date`.

### Future dates

Future dates that do not have a published rate return:

```json
{
  "error": "RATE_NOT_FOUND",
  "message": "Exchange rate could not be found for the requested date."
}
```

### Dates before the series starts

Dates for which the upstream has no available rate return `RATE_NOT_FOUND`.

### Currency codes

Currency codes are normalized to uppercase.

Invalid currency formats return:

```text
INVALID_CURRENCY
```

The service expects three-letter alphabetic currency codes.

### Same currency

A conversion such as EUR → EUR does not require an upstream request.

The rate is `1` and the result equals the original amount.

The response source is:

```text
same_currency
```

### Amount validation

The following amounts are rejected:

* zero
* negative values
* values with more than 10 decimal places

An amount with exactly 10 decimal places is accepted.

Invalid amounts return:

```text
INVALID_AMOUNT
```

### Upstream failures

The service does not invent or estimate exchange rates.

| Situation                           | Error code                  | HTTP status |
| ----------------------------------- | --------------------------- | ----------: |
| Invalid amount                      | `INVALID_AMOUNT`            |         400 |
| Invalid currency                    | `INVALID_CURRENCY`          |         400 |
| Rate unavailable for requested date | `RATE_NOT_FOUND`            |         404 |
| Upstream timeout                    | `UPSTREAM_TIMEOUT`          |         504 |
| Upstream request failure            | `UPSTREAM_UNAVAILABLE`      |         502 |
| Upstream HTTP error                 | `UPSTREAM_ERROR`            |         502 |
| Invalid upstream response           | `INVALID_UPSTREAM_RESPONSE` |         502 |

All application errors use the following structure:

```json
{
  "error": "<machine_code>",
  "message": "<human-readable message>"
}
```

### Repeated requests

Rates are cached using the currency pair and requested date as the cache key.

A repeated request for the same pair and date uses the cached rate instead of requesting the upstream service again.

The cache has a 300-second TTL.

## Tests

Run the test suite with:

```bash
./test.sh
```

The tests do not require network access.

The upstream HTTP layer is mocked using `httpx.MockTransport`, so tests remain deterministic and do not depend on the real Frankfurter API.

The test suite can also be run while pointing `FX_UPSTREAM_BASE` at a closed port:

```bash
FX_UPSTREAM_BASE=http://127.0.0.1:59999 ./test.sh
```

The tests should still pass because they do not make real upstream requests.

Current test suite:

```text
23 passed
```

## Project structure

```text
mangolab-fx-tool/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── errors.py
│   ├── cache.py
│   └── services/
│       └── fx_service.py
├── tests/
│   ├── conftest.py
│   ├── test_convert.py
│   └── test_api.py
├── run.sh
├── test.sh
├── requirements.txt
├── README.md
├── NOTES.md
└── REVIEW.md
```
