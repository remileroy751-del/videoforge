# -*- mode: python ; coding: utf-8 -*-
"""
Fichier .spec PyInstaller pour Ty-Videos-Studio.

Pourquoi un .spec plutôt que des options --collect-all / --copy-metadata
en ligne de commande ?

`--copy-metadata <paquet>` échoue (et arrête TOUTE la compilation) dès
qu'un seul des paquets demandés n'est pas installé sous exactement ce
nom de distribution dans l'environnement de build (ex. "requests" peut
ne pas être présent selon la version résolue de huggingface_hub). Ici,
chaque appel est protégé individuellement : si un paquet est absent, on
l'ignore simplement (avec un message dans le journal de build) au lieu
de faire échouer toute la compilation.
"""
from PyInstaller.utils.hooks import collect_all, copy_metadata

# Paquets pour lesquels on veut tout récupérer (sous-modules, données,
# bibliothèques natives). Nom d'IMPORT (avec underscore le cas échéant).
COLLECT_ALL_PACKAGES = [
    "customtkinter",
    "moviepy",
    "imageio",
    "imageio_ffmpeg",
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "huggingface_hub",
    "onnxruntime",
    "av",
    "certifi",
]

# Paquets pour lesquels on veut au minimum les métadonnées (évite les
# erreurs "PackageNotFoundError" au lancement de l'exécutable). Nom de
# DISTRIBUTION pip (avec tiret le cas échéant).
COPY_METADATA_PACKAGES = [
    "imageio",
    "imageio-ffmpeg",
    "moviepy",
    "faster-whisper",
    "ctranslate2",
    "tokenizers",
    "huggingface-hub",
    "numpy",
    "tqdm",
    "requests",
    "packaging",
    "filelock",
    "pyyaml",
    "regex",
]

datas = [("assets", "assets")]
binaries = []
hiddenimports = []

for pkg in COLLECT_ALL_PACKAGES:
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception as e:
        print(f"[Ty-Videos-Studio.spec] collect_all ignoré pour '{pkg}' : {e}")

for pkg in COPY_METADATA_PACKAGES:
    try:
        datas += copy_metadata(pkg)
    except Exception as e:
        print(f"[Ty-Videos-Studio.spec] copy_metadata ignoré pour '{pkg}' (paquet absent) : {e}")

block_cipher = None

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Ty-Videos-Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["assets/app.ico"],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Ty-Videos-Studio",
)
