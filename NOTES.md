# Notes

## Decisions

Python and FastAPI were chosen because the task requires a small HTTP service with a single tool-like endpoint. FastAPI provides simple request validation and async HTTP support.

The upstream URL and port are configurable through environment variables so the service does not depend on a hardcoded deployment environment.

For exchange rates, the service keeps `asked_date` and `rate_date` separate. If no rate is available for the requested date, the service returns `RATE_NOT_FOUND` instead of silently using a previous day's rate. This avoids presenting an older published rate as if it belonged to the requested date.

Same-currency conversions are handled locally with a rate of `1`, without calling the upstream service. Responses from the upstream are cached by currency pair and requested date to avoid unnecessary repeated requests.

## With another day

If I had another day, I would add an optional "latest available rate" fallback for weekends and holidays. The fallback would search for the most recent published rate before the requested date, but it would clearly communicate that the requested date was unavailable and expose the actual `rate_date`.

I would also add more API-level tests for upstream failures, validation errors, and fallback behaviour.

## AI tools

I used both ChatGPT and Claude during the implementation, but for different purposes.

I used Claude as a technical-lead and mentor-style assistant. I provided it with the project requirements and used it to discuss architecture, implementation steps, engineering decisions, and how to approach the case study. I also used a structured prompt to have Claude guide me through the project as a technical mentor.

I used ChatGPT more actively during implementation to discuss specific code decisions, validation rules, caching, error handling, test cases, and debugging. I also used it to review decisions and verify the implementation against the case requirements.

The free version of Claude had usage limitations that sometimes interrupted the flow and slowed down the implementation. Because of this, I used ChatGPT alongside Claude to continue the work and resolve implementation details more efficiently.

In both cases, I treated the AI tools as assistants rather than sources of truth. I reviewed their suggestions, ran the code locally, checked the test results, and made the final implementation decisions myself.


## One thing the AI got wrong

During the discussion about missing rates on weekends and holidays, the AI suggested that using the most recently published rate could be a possible approach.

I questioned this because a user asking for a specific date could interpret the returned value as the rate for that date, even if it was actually published earlier. We decided not to silently substitute an older rate. Instead, the service returns `RATE_NOT_FOUND` when no rate is available for the requested date and keeps `asked_date` and `rate_date` separate whenever they differ.

This was a useful example of treating AI suggestions as something to evaluate rather than simply implement.

