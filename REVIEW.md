# Review of tool.py

## 1.

**Cache does not include the requested date.**

**What is wrong:** The cache key only uses the currency pair, such as `EUR-TRY`. The requested date is not included in the key, and cached values are kept until the application restarts.

**Customer impact:** A rate requested for one date can be returned for another date. For example, if a customer first requests a historical EUR/TRY rate, another customer requesting a different date may receive the cached rate from the first request. This can lead to an incorrect conversion.

**How I would verify:** I would request the same currency pair for two different dates and use a mock upstream that returns different rates for each date. I would check whether the second request incorrectly returns the first rate.

## 2.

**Errors are hidden and returned as a successful response.**

**What is wrong:** The endpoint catches every exception and returns `200 OK` with `rate: 0.0` and `result: 0.0`.

**Customer impact:** A customer or an agent using this service may think the conversion succeeded when it actually failed. For example, an upstream service failure could result in a conversion of `0.0` instead of an error. A downstream system may then continue using this incorrect result.

**How I would verify:** I would make the upstream service return an error or invalid response and check the HTTP status and response body. The current implementation would still return a successful response with zero values.

## 3.

**The exchange rate is rounded before the calculation.**

**What is wrong:** The code rounds the exchange rate to two decimal places before multiplying it by the requested amount.

**Customer impact:** For exchange rates with more than two decimal places, this can change the final conversion result. The difference can become significant when converting large amounts.

**How I would verify:** I would use a mocked rate with several decimal places and a large amount. I would compare the result from this service with the result calculated using the original, unrounded rate.

## The one I would fix before shipping tonight

**I would fix the cache key first.**

The reason is that this can return an incorrect exchange rate even when the upstream service and the application are working normally. A customer could receive a rate from a different date without any indication that the value is wrong.

For tonight, I would at least include the requested date in the cache key. I would also add a test for two requests using the same currency pair but different dates.

## Things that look suspicious but are fine

**The in-memory cache itself is not necessarily a problem.** For a small service, an in-process cache can be a reasonable way to reduce repeated upstream requests. The main problem is how the cache key is constructed.

**The global `httpx.AsyncClient` is worth reviewing, but I would not treat it as the main customer-facing defect for this case.** It would be better to manage its lifecycle explicitly, but it is not as directly harmful as returning incorrect exchange rates.

**The lack of a cache size limit is also worth monitoring.** The dictionary can grow over time, but I would prioritize the correctness problem with the cache key before treating memory usage as a major customer issue.

