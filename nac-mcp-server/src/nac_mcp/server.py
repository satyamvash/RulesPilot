"""NAC MCP Server entrypoint."""
import logging
import sys
import os

# Allow running as a script directly (e.g. mcp dev src/nac_mcp/server.py)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from mcp.server.fastmcp import FastMCP
from nac_mcp.tools import rules, settings, csv_tools, meta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("nac_mcp")

mcp = FastMCP("NAC App Control")

rules.register(mcp)
settings.register(mcp)
csv_tools.register(mcp)
meta.register(mcp)

_tool_count = len(mcp._tool_manager._tools)
log.info("NAC MCP server initialized — %d tools registered", _tool_count)


def main() -> None:
    log.info("NAC MCP server starting (transport: stdio)")
    mcp.run()


if __name__ == "__main__":
    main()
