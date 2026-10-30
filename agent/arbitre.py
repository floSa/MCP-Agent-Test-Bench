"""L'arbitre anti-triche.

Principe : le LLM n'est JAMAIS cru sur parole. L'arbitre maintient l'état réel
du calcul (la formule courante, le dernier résultat d'outil) et :

1. vérifie chaque appel d'outil AVANT de l'exécuter : bon enchaînement
   (convertir -> trouver -> calculer -> remplacer), bons arguments
   (le calcul demandé est bien LE calcul prioritaire de la formule courante) ;
2. vérifie la réponse finale : elle n'est acceptée que si la formule a été
   entièrement réduite, étape par étape, par les outils, et que le nombre
   annoncé est celui obtenu par cette réduction.

Pour connaître la vérité terrain (quel est le calcul prioritaire ?), l'arbitre
interroge lui-même le serveur MCP — déterministe — via `oracle_priorite`,
plutôt que de faire confiance à ce que le LLM raconte.
"""

import re


def normaliser_pour_comparer(formule) -> str:
    """Compare « 3*4+2 » et « 3 * 4 + 2 » comme identiques."""
    avec_espaces = re.sub(r"([()+\-*/])", r" \1 ", str(formule))
    return " ".join(avec_espaces.split())


def _fmt(nombre) -> str:
    """12.0 -> '12', 2.5 -> '2.5' (pour écrire des consignes lisibles)."""
    nombre = float(nombre)
    return str(int(nombre)) if nombre.is_integer() else str(nombre)


def est_nombre(texte: str) -> bool:
    return re.fullmatch(r"-?\d+(\.\d+)?", str(texte).strip()) is not None


def extraire_nombre_final(contenu: str):
    """Cherche le nombre annonce dans « REPONSE FINALE: 14 » (avec tolerance)."""
    if not contenu:
        return None
    motif = re.search(r"REPONSE\s*FINALE\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)",
                      contenu, re.IGNORECASE)
    if motif:
        return float(motif.group(1).replace(",", "."))
    nombres = re.findall(r"-?\d+(?:[.,]\d+)?", contenu)
    if nombres:
        return float(nombres[-1].replace(",", "."))
    return None


# Les deux outils de conversion (pur Python deterministe et LLM de secours)
# jouent le meme role pour l'arbitre : produire la formule initiale. On les
# traite donc de maniere interchangeable comme « premiere etape ».
OUTILS_CONVERSION = {"convertir_texte_en_formule",
                     "convertir_texte_en_formule_libre"}


class Arbitre:
    def __init__(self, oracle_priorite):
        # oracle_priorite : fonction async (formule) -> dict, branchée sur
        # l'outil MCP trouver_calcul_prioritaire (vérité terrain).
        self._oracle = oracle_priorite
        self.formule_initiale = None
        self.formule_courante = None
        self.dernier_calcul = None   # {"sous_expression": ..., "resultat": ...}
        self._priorite_validee = None
        # Réponse du serveur MCP à trouver_calcul_prioritaire pour la formule
        # courante (remise à zéro quand la formule change).
        self._priorite_connue = None

    # -- vérification AVANT exécution d'un outil ----------------------------

    async def verifier_appel(self, nom: str, args: dict):
        """Renvoie un message de refus (str), ou None si l'appel est autorisé.

        Chaque refus indique la prochaine étape attendue : sans cela, un modèle
        qui s'est perdu répète le même appel indéfiniment.
        """
        refus = await self._verifier_appel(nom, args)
        return None if refus is None else f"{refus} {self.indice()}"

    def indice(self) -> str:
        """Prochaine étape attendue, déduite de l'état RÉEL (jamais du LLM)."""
        courante = self.formule_courante
        if courante is None:
            return "Appelle convertir_texte_en_formule."
        if self.dernier_calcul is not None:
            d = self.dernier_calcul
            return ("Appelle remplacer_calcul_par_resultat avec "
                    f"formule = « {courante} », "
                    f"sous_expression = « {d['sous_expression']} », "
                    f"valeur = {_fmt(d['resultat'])}.")
        if est_nombre(courante):
            return "La formule est réduite : réponds « REPONSE FINALE: <nombre> »."
        p = self._priorite_connue
        if p is not None:
            return ("Appelle calculer avec "
                    f"gauche = {_fmt(p['gauche'])}, "
                    f"operateur = « {p['operateur']} », "
                    f"droite = {_fmt(p['droite'])}.")
        return f"Appelle trouver_calcul_prioritaire avec formule = « {courante} »."

    async def _verifier_appel(self, nom: str, args: dict):
        if nom in OUTILS_CONVERSION:
            if self.formule_courante is not None:
                return ("Refusé : le texte a déjà été converti. La formule "
                        f"courante est « {self.formule_courante} ».")
            return None

        if self.formule_courante is None:
            return "Refusé : commence par appeler convertir_texte_en_formule."

        if nom == "trouver_calcul_prioritaire":
            if not self._meme_formule(args.get("formule")):
                return (f"Refusé : la formule courante est "
                        f"« {self.formule_courante} », pas "
                        f"« {args.get('formule')} ».")
            if self._priorite_connue is not None or self.dernier_calcul is not None:
                return "Refusé : cette étape est déjà faite."
            return None

        if nom == "calculer":
            priorite = await self._oracle(self.formule_courante)
            if priorite.get("termine"):
                return ("Refusé : la formule est déjà réduite à un seul nombre. "
                        "Donne la réponse finale.")
            try:
                gauche = float(args.get("gauche"))
                droite = float(args.get("droite"))
            except (TypeError, ValueError):
                return "Refusé : gauche et droite doivent être des nombres."
            if (args.get("operateur") != priorite["operateur"]
                    or abs(gauche - float(priorite["gauche"])) > 1e-9
                    or abs(droite - float(priorite["droite"])) > 1e-9):
                return (f"Refusé : ce n'est pas le calcul prioritaire. Le calcul "
                        f"attendu est « {priorite['sous_expression']} ».")
            self._priorite_validee = priorite
            return None

        if nom == "remplacer_calcul_par_resultat":
            if not self._meme_formule(args.get("formule")):
                return (f"Refusé : la formule courante est "
                        f"« {self.formule_courante} ».")
            if self.dernier_calcul is None:
                return "Refusé : utilise d'abord l'outil calculer."
            attendu = self.dernier_calcul
            if (normaliser_pour_comparer(args.get("sous_expression"))
                    != normaliser_pour_comparer(attendu["sous_expression"])):
                return (f"Refusé : la sous-expression à remplacer est "
                        f"« {attendu['sous_expression']} ».")
            try:
                valeur = float(args.get("valeur"))
            except (TypeError, ValueError):
                return "Refusé : valeur doit être un nombre."
            if abs(valeur - attendu["resultat"]) > 1e-6:
                return ("Refusé : cette valeur n'est pas le résultat renvoyé "
                        "par l'outil calculer.")
            return None

        return f"Refusé : outil inconnu « {nom} »."

    # -- mise à jour de l'état APRÈS exécution réussie -----------------------

    def noter_resultat(self, nom: str, args: dict, resultat) -> None:
        if nom in OUTILS_CONVERSION:
            self.formule_courante = str(resultat)
            self.formule_initiale = str(resultat)
            self._priorite_connue = None
        elif nom == "trouver_calcul_prioritaire":
            if isinstance(resultat, dict) and not resultat.get("termine"):
                self._priorite_connue = resultat
        elif nom == "calculer":
            self.dernier_calcul = {
                "sous_expression": self._priorite_validee["sous_expression"],
                "resultat": float(resultat),
            }
        elif nom == "remplacer_calcul_par_resultat":
            self.formule_courante = str(resultat)
            self.dernier_calcul = None
            self._priorite_connue = None

    # -- vérification de la réponse finale -----------------------------------

    def verifier_reponse_finale(self, valeur):
        """Renvoie un message de refus (str), ou None si la réponse est valide."""
        if self.formule_courante is None:
            return ("Refusé : aucune formule n'a été construite. Commence par "
                    "convertir_texte_en_formule.")
        if not est_nombre(self.formule_courante):
            return (f"Refusé : la formule « {self.formule_courante} » n'est pas "
                    "encore réduite à un seul nombre. Continue avec "
                    "trouver_calcul_prioritaire.")
        if valeur is None:
            return ("Refusé : aucun nombre trouvé dans ta réponse. Termine par "
                    "« REPONSE FINALE: <nombre> ».")
        if abs(float(valeur) - float(self.formule_courante)) > 1e-6:
            return ("Refusé : ce nombre ne correspond pas à la formule réduite "
                    "par les outils.")
        return None

    def _meme_formule(self, formule) -> bool:
        return (normaliser_pour_comparer(formule)
                == normaliser_pour_comparer(self.formule_courante))
