"""Diagnóstico do relay oficial Unity via protocolo MCP, sem mexer em cenas."""
import asyncio
import json
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def executar():
    servidor = StdioServerParameters(command=r"C:\Users\vinic\.unity\relay\relay_win.exe", args=["--mcp"])
    async with stdio_client(servidor) as (entrada, saida):
        async with ClientSession(entrada, saida) as sessao:
            inicio = await sessao.initialize()
            if len(sys.argv) > 1:
                resposta = await sessao.call_tool("Unity_RunCommand", {"Code": Path(sys.argv[1]).read_text(encoding="utf-8"), "Title": "Bancada de validação VRmed"})
                for item in resposta.content:
                    if item.type == "text":
                        dados = json.loads(item.text)
                        detalhe = dados.get("data", {})
                        print(json.dumps({"success": dados.get("success"), "logs": detalhe.get("executionLogs"),
                                          "compilacao": detalhe.get("compilationLogs")}, ensure_ascii=False))
            else:
                ferramentas = await sessao.list_tools()
                print(json.dumps({"servidor": inicio.model_dump(), "ferramentas": ferramentas.model_dump()}, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(executar(), timeout=55))
