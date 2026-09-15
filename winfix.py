"""
Correctif pour l'exécution de sous-processus (FFmpeg, etc.) dans une
application PyInstaller compilée en mode --windowed (sans console) sous
Windows.

CAUSE DU BUG « Production en cours… » qui ne se termine jamais :
Dans un exécutable Windows sans console, les handles standard (stdin/
stdout/stderr) du processus parent sont invalides ou absents. Quand
Python lance un sous-processus (FFmpeg, appelé directement par ce
logiciel ou en interne par MoviePy) sans rediriger explicitement son
entrée standard, Windows peut lui transmettre un handle d'entrée
invalide. FFmpeg, qui lit en permanence son entrée standard pour
détecter des commandes clavier (ex. "q" pour arrêter), reste alors
bloqué indéfiniment en attente d'une entrée qui n'arrivera jamais : la
vidéo n'est jamais produite et l'application affiche "Production en
cours…" pour toujours, sans jamais afficher d'erreur.

Ce module corrige cela en forçant, pour TOUT sous-processus lancé par
l'application (y compris ceux lancés en interne par MoviePy), une
entrée standard fermée (DEVNULL) et l'absence de fenêtre de console
parasite. Il doit être importé en tout premier, avant tout autre
module qui pourrait invoquer subprocess (moviepy, edge-tts, etc.),
pour être sûr d'être actif avant le premier appel.
"""
from __future__ import annotations
import os
import subprocess

if os.name == "nt":
    _original_popen_init = subprocess.Popen.__init__

    def _safe_popen_init(self, *args, **kwargs):
        # N'écrase jamais une valeur déjà fournie explicitement par l'appelant.
        kwargs.setdefault("stdin", subprocess.DEVNULL)
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
        return _original_popen_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = _safe_popen_init
