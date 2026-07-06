import asyncio
from google.adk.tools import McpToolset
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_toolset import StdioConnectionParams

async def main():
    t = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command='npx',
                args=['-y', '@anthropic-ai/google-developer-knowledge-mcp']
            )
        )
    )
    tools = await t.get_tools()
    print([tool.name for tool in tools])
    await t.close()

asyncio.run(main())
