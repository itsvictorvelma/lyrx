"""Starts the Lyrx server on the local address from `config.py`."""

import uvicorn

from lyrx import config
from lyrx.app import create_app


def main() -> None:
    uvicorn.run(create_app(), host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
