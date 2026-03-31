"""Entry point for ``python -m zero_mcp`` and the ``zero-mcp`` console script."""

import asyncio


def main() -> None:
    """Launch the Zero MCP server over stdio."""
    from .server import main as server_main

    asyncio.run(server_main())


if __name__ == "__main__":
    main()
