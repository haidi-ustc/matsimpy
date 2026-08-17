"""Unit metadata helpers."""

from functools import wraps


def unitized(unit: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.unit = unit
        return wrapper

    return decorator
