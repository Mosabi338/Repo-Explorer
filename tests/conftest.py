import pytest

from app.cache import clear_cache


@pytest.fixture(autouse=True)
def empty_cache_before_each_test():
    """Start every test with an empty cache so tests can't affect each other."""
    clear_cache()