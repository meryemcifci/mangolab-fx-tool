#testlerin kullanabileceği hazır bir FXService oluşturuyorum.
import pytest

from app.cache import TTLCache
from app.services.fx_service import FXService


@pytest.fixture
def cache():
    return TTLCache(ttl_seconds=300)


@pytest.fixture
def fx_service(cache):
    return FXService(cache=cache)