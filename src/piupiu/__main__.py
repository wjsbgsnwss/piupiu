import asyncio
import logging

from .config import get_settings
from .agent import Agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-30s  %(levelname)s  %(message)s",
)


def main() -> None:
    cfg = get_settings()
    agent = Agent(cfg)
    asyncio.run(agent.run())


if __name__ == "__main__":
    main()
