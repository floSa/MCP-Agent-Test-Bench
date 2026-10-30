"""Petit client LLM pour le serveur MCP (API /v1 : Ollama ou vLLM).

Sert a l'outil « LLM » de demonstration : convertir une expression en langage
naturel LIBRE en formule, quand le parseur deterministe ne couvre pas la
formulation. Volontairement minimal : une seule fonction, synchrone.

Le serveur MCP ne FAIT PAS confiance a la sortie du LLM : la formule proposee
ici est ensuite validee par le tokeniseur deterministe (voir calculatrice.py).
C'est le coeur du patron de robustesse « le LLM propose, le code dispose ».
"""

import json
import os
import re

import httpx

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma4:e4b")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "inutile")
LLM_EXTRA_BODY = json.loads(os.environ.get("LLM_EXTRA_BODY") or "{}")

# On demande UNIQUEMENT la formule, en symboles, sans phrase autour.
_PROMPT = """Tu convertis une expression mathematique ecrite en langage naturel en une formule.
Regles STRICTES :
- n'utilise que des chiffres et les symboles + - * / ( ) et l'espace ;
- conserve les parentheses et les priorites de l'expression d'origine ;
- ne calcule rien, ne simplifie rien : traduis seulement ;
- reponds UNIQUEMENT la formule, sans phrase, sans texte autour.

Exemples :
"trois fois quatre plus deux" -> 3 * 4 + 2
"le double de cinq" -> 2 * 5
"la moitie de huit plus un" -> 8 / 2 + 1

Expression : "%s"
Formule :"""


def proposer_formule(texte: str) -> str:
    """Demande au LLM une formule pour `texte` et renvoie la chaine brute.

    Ne valide rien : c'est l'appelant (calculatrice.py) qui passe le resultat au
    tokeniseur deterministe. On se contente d'extraire une ligne plausible.
    """
    with httpx.Client(timeout=httpx.Timeout(120.0)) as http:
        reponse = http.post(
            f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": _PROMPT % texte}],
                "temperature": 0,
                # marge pour les modeles qui « reflechissent » avant de repondre
                "max_tokens": 512,
                **LLM_EXTRA_BODY,
            },
        )
        reponse.raise_for_status()
        brute = reponse.json()["choices"][0]["message"].get("content") or ""

    # On garde la premiere ligne non vide qui ressemble a une formule, et on
    # ne conserve que les caracteres autorises (chiffres, operateurs, parentheses).
    # De toute facon, calculatrice.py revalide tout : ici on degrossit seulement.
    for ligne in brute.splitlines():
        ligne = ligne.split("=")[0]   # ignore une eventuelle partie « = resultat »
        candidat = "".join(re.findall(r"[0-9+\-*/().\s]", ligne))
        candidat = re.sub(r"\s+", " ", candidat).strip()
        # Une formule contient forcement au moins un chiffre : on ignore les
        # lignes de prose ou un operateur isole que le modele aurait ajoutes.
        if candidat and any(c.isdigit() for c in candidat):
            return candidat
    return brute.strip()
