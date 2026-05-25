import asyncio
import logging

from .config import get_settings
from .agent import Agent

# Third-party libraries that flood the console even at WARNING — keep them quiet.
_SILENT_LOGGERS = (
    "presidio-analyzer",
    "presidio_analyzer",
    "spacy",
    "httpx",
    "httpcore",
    "aiogram",
    "asyncio",
)


def _configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.ERROR
    fmt = "%(asctime)s  %(name)-40s  %(levelname)-8s  %(message)s"
    logging.basicConfig(level=level, format=fmt, force=True)
    for lib in _SILENT_LOGGERS:
        logging.getLogger(lib).setLevel(logging.ERROR)


def main() -> None:
    cfg = get_settings()
    _configure_logging(cfg.debug)
    agent = Agent(cfg)
    asyncio.run(agent.run())


if __name__ == "__main__":
    main()
