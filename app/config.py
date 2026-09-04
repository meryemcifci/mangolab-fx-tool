import os


UPSTREAM_BASE_URL = os.getenv(  #environment variable
    "FX_UPSTREAM_BASE",
    "https://api.frankfurter.dev",
)

PORT = int(os.getenv("PORT", "8080"))