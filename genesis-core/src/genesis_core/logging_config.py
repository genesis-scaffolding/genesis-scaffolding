import logging

NOISY_LOGGERS = [
    "uvicorn",
    "uvicorn.access",
    "uvicorn.error",
    "fastapi",
    "LiteLLM",
    "litellm",
    "httpx",
    "httpcore",
]


def setup_logging(log_level="warning"):
    # Suppress noisy third-party loggers
    for noisy_logger in NOISY_LOGGERS:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    root_logger = logging.getLogger()
    # Ensure basicConfig runs once (creates handler if missing)
    if not root_logger.handlers:
        logging.basicConfig(
            format="[%(name)s] %(levelname)s: %(message)s",
        )

    # Apply level to root
    root_logger.setLevel(log_level)

    # Log the logging level
    root_logger.info("Setup root logger at %s level", log_level)
