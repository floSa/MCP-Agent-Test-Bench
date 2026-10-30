# MCPJam, l'inspecteur de serveurs MCP

[MCPJam](https://github.com/mcpjam/inspector) est une interface web qui se
connecte à **n'importe quel serveur MCP**, liste ses outils et permet de les
**appeler à la main**, sans LLM et sans écrire de code.

C'est le premier réflexe de test : avant de brancher un serveur MCP sur
l'agent, on vérifie qu'il expose les bons outils et qu'ils répondent comme prévu.

## Ouvrir MCPJam

La stack étant démarrée (`make up`) : <http://localhost:6274>

## Connecter le serveur de la calculatrice

| Champ | Valeur |
|---|---|
| Transport | HTTP (« Streamable HTTP » selon les versions) |
| URL | `http://mcp-calculatrice:8000/mcp/` |

Le nom d'hôte est celui du **service Docker**, pas `localhost` : la connexion
part du conteneur MCPJam, qui partage le réseau Docker avec le serveur MCP. Le
slash final de `/mcp/` est nécessaire.

## Essayer les outils

Cinq outils apparaissent. MCPJam génère un formulaire à partir de leur
**schéma** (les paramètres typés).

| Outil | Arguments | Résultat |
|---|---|---|
| `convertir_texte_en_formule` | `texte = "trois fois quatre plus deux"` | `"3 * 4 + 2"` |
| `trouver_calcul_prioritaire` | `formule = "3 * 4 + 2"` | le calcul `3 * 4` |
| `calculer` | `gauche = 3`, `operateur = "*"`, `droite = 4` | `12` |
| `remplacer_calcul_par_resultat` | `formule = "3 * 4 + 2"`, `sous_expression = "3 * 4"`, `valeur = 12` | `"12 + 2"` |

L'agent enchaîne exactement ces appels, mais c'est le LLM qui choisit l'outil et
remplit les arguments.

## Constater que les garde-fous sont dans les outils

Appeler `remplacer_calcul_par_resultat` avec une **valeur fausse**
(`valeur = 99`) ou une sous-expression **non prioritaire**
(`sous_expression = "4 + 2"`) : l'outil refuse. Appeler `calculer` avec
`operateur = "/"` et `droite = 0` : message clair « Division par zero
impossible ». Ces protections s'appliquent même sans LLM.

## Dépannage

- **La page ne s'ouvre pas** : `docker compose ps`, puis vérifier le port 6274.
- **« Connection failed »** : vérifier l'URL (slash final) et que le serveur est
  *healthy*. Test depuis l'hôte : `curl http://localhost:8101/sante`.
- **Aucun outil listé** : le serveur a peut-être redémarré, reconnecter-le.
