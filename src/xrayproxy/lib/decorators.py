import asyncio
from functools import wraps
from logging import Logger
from typing import Any, Callable


def error_logging(logger: Logger) -> Callable:  # type: ignore
    def _error_logging(func: Callable) -> Callable:  # type: ignore
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.error(e, exc_info=True)

            return wrapper
        else:

            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(e, exc_info=True)

            return wrapper

    return _error_logging
