from collections.abc import Awaitable, Callable
from functools import wraps
from logging import Logger
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def error_logging(logger: Logger) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R | None]]]:
    def _error_logging(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R | None]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(e, exc_info=True)
                return None

        return wrapper

    return _error_logging
