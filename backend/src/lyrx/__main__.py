"""Starts the Lyrx server on the address from `config.py`."""

import logging

import uvicorn

from lyrx import config
from lyrx.app import create_app


def main() -> None:
    logging.basicConfig(format=config.LOG_FORMAT)
    logging.getLogger("lyrx").setLevel(config.LOG_LEVEL)
    # uvicorn trusts `X-Forwarded-For` from 127.0.0.1 by default; only the configured proxy
    # (Caddy, spec 020) may name the client, and with none set the header is ignored.
    uvicorn.run(
        create_app(),
        host=config.HOST,
        port=config.PORT,
        proxy_headers=config.TRUSTED_PROXY is not None,
        forwarded_allow_ips=config.TRUSTED_PROXY or "",
    )


if __name__ == "__main__":
    main()
