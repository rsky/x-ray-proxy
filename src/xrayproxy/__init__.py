import logging.config

# Set log level for httpx and httpcore to WARNING
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {
            "httpx": {
                "level": "WARNING",
            },
            "httpcore": {
                "level": "WARNING",
            },
        },
    }
)
