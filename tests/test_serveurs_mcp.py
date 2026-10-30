"""Niveau 1 — les serveurs MCP d'exemple, testés en mémoire (sans réseau)."""

from fastmcp import Client

import maths
import texte


async def test_outils_maths_exposes():
    async with Client(maths.mcp) as client:
        noms = {o.name for o in await client.list_tools()}
    assert noms == {"additionner", "multiplier"}


async def test_additionner_et_multiplier():
    async with Client(maths.mcp) as client:
        assert (await client.call_tool("additionner", {"a": 2, "b": 3})).data == 5
        assert (await client.call_tool("multiplier", {"a": 4, "b": 3})).data == 12


async def test_outils_texte():
    async with Client(texte.mcp) as client:
        majuscules = await client.call_tool("mettre_en_majuscules",
                                            {"texte": "bonjour"})
        mots = await client.call_tool("compter_mots", {"texte": "un deux trois"})
    assert majuscules.data == "BONJOUR"
    assert mots.data == 3
