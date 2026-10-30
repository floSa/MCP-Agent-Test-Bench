# MCPJam, l'inspecteur de serveurs MCP

[MCPJam](https://github.com/mcpjam/inspector) est une interface web qui se
connecte à **n'importe quel serveur MCP**, liste ses outils et permet de les
**appeler à la main**, sans LLM et sans écrire de code.

C'est le premier réflexe de test : avant de brancher un serveur MCP sur
l'agent, on vérifie qu'il expose les bons outils et qu'ils répondent comme prévu.

## Ouvrir MCPJam

La stack étant démarrée (`make up`) : <http://localhost:6274>

## Connecter un serveur

| Champ | Valeur |
|---|---|
| Transport | HTTP (« Streamable HTTP » selon les versions) |
| URL | `http://mcp-maths:8000/mcp/` (ou `http://mcp-texte:8000/mcp/`) |

Le nom d'hôte est celui du **service Docker**, pas `localhost` : la connexion
part du conteneur MCPJam, qui partage le réseau Docker avec les serveurs MCP.
Le slash final de `/mcp/` est nécessaire.

## Essayer les outils

Après connexion, MCPJam affiche les outils et génère un formulaire à partir de
leur **schéma** (les paramètres typés).

| Serveur | Outil | Arguments | Résultat |
|---|---|---|---|
| mcp-maths | `additionner` | `a = 12`, `b = 30` | `42` |
| mcp-maths | `multiplier` | `a = 4`, `b = 3` | `12` |
| mcp-texte | `mettre_en_majuscules` | `texte = "salut"` | `"SALUT"` |
| mcp-texte | `compter_mots` | `texte = "un deux trois"` | `3` |

L'agent fait exactement la même chose, mais c'est le LLM qui choisit l'outil et
remplit les arguments.

## Dépannage

- **La page ne s'ouvre pas** : `docker compose ps`, puis vérifier le port 6274.
- **« Connection failed »** : vérifier l'URL (slash final) et que le serveur est
  *healthy*. Test depuis l'hôte : `curl http://localhost:8101/sante`.
- **Aucun outil listé** : le serveur a peut-être redémarré, reconnecter-le.
