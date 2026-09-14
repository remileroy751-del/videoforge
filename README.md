# Ty-Videos-Studio — Windows

Application de bureau pour créer facilement des vidéos verticales **9:16** ou horizontales **16:9**.

## Fonctions
- Images ou vidéos comme fond, scène par scène
- 3 modes texte : sans texte, texte complet avec effet machine à écrire, sous-titres
- Effet Ken Burns sur les images
- Voix off française via Edge TTS
- Musique de fond en boucle avec volume réduit
- Gestion de plusieurs scènes
- Duplication/suppression de scènes
- Sauvegarde et ouverture de projets JSON
- Export MP4
- Interface moderne sombre/claire
- Packaging Windows avec installateur et raccourci Bureau

Le moteur reprend les principes du fichier source fourni : formats 9:16/16:9, fonds image/vidéo, trois modes de texte, zoom et voix/musique.

## Compilation sans PowerShell

1. Crée un dépôt GitHub.
2. Envoie tout le contenu de ce dossier dans le dépôt.
3. Va dans **Actions**.
4. Lance **Build Windows**.
5. Télécharge l'artefact `Ty-Videos-Studio-Windows`.
6. Tu obtiendras un installateur `.exe`.
7. Lance l'installateur : il crée automatiquement le raccourci sur le Bureau.

### Important
FFmpeg est installé par le workflow GitHub et intégré au dossier de l'application.
Edge TTS nécessite une connexion Internet pour générer les voix.

Le clonage vocal XTTS n'est pas inclus par défaut dans le build Windows afin d'éviter un installateur de plusieurs gigaoctets et des incompatibilités de version. Il peut être ajouté comme module optionnel dans une future version.


### Correction démarrage Windows

Le workflow inclut les métadonnées de `imageio`, `imageio-ffmpeg` et `moviepy`. MoviePy charge ImageIO au démarrage et ImageIO recherche sa version via `importlib.metadata`. Sans ces métadonnées, PyInstaller peut provoquer `PackageNotFoundError: No package metadata was found for imageio`.


### Production vidéo
FFmpeg est inclus dans la compilation Windows via imageio-ffmpeg. L’utilisateur final n’a pas besoin d’installer FFmpeg séparément. Edge TTS nécessite Internet.


La console de production est fixée en bas de la fenêtre et affiche les étapes du rendu. En cas d'erreur, un message détaillé est affiché.
