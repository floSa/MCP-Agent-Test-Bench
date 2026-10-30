import os
import pathlib
import socket
import subprocess
import sys
import time

import httpx
import pytest

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))                  # paquet `agent`
sys.path.insert(0, str(RACINE / "mcp_servers"))  # modules `calculatrice`, `outils_calcul`
sys.path.insert(0, str(RACINE / "tests"))        # `faux_llm`


@pytest.fixture(scope="session")
def url_mcp():
    """Lance le VRAI serveur MCP de la calculatrice (HTTP) le temps des tests."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    processus = subprocess.Popen(
        [sys.executable, str(RACINE / "mcp_servers" / "calculatrice.py")],
        env={**os.environ, "PORT": str(port)},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                httpx.get(f"http://127.0.0.1:{port}/sante", timeout=1)
                break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            pytest.fail("serveur MCP injoignable")
        yield f"http://127.0.0.1:{port}/mcp/"
    finally:
        processus.terminate()
