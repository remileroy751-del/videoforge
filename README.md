# Ty-Videos-Studio — Windows

Application de bureau pour créer facilement des vidéos verticales **9:16** ou horizontales **16:9**.

## Deux modes de production

### 1. Scènes + texte
- Images ou vidéos comme fond, scène par scène
- 3 modes texte : sans texte, texte complet avec effet machine à écrire, sous-titres
- Voix off générée automatiquement à partir du texte (Edge TTS, français)
- Gestion de plusieurs scènes (ajout, duplication, suppression)

### 2. Voix off + photos/vidéos (nouveau)
Pour produire une vidéo à partir d'une voix off déjà enregistrée :
- Importer un fichier audio existant (MP3, AAC ou WAV)
- Ajouter une ou plusieurs photos/vidéos de fond (réparties automatiquement
  sur toute la durée de la voix off, effet Ken Burns sur les images)
- Choisir l'affichage des sous-titres : **Aucun**, **Classique** (bas
  d'écran, encadré) ou **Dynamique** (texte coloré, plus grand)
- Les sous-titres sont générés **automatiquement** par reconnaissance
  vocale (transcription du fichier importé), aucune saisie de texte requise
- Lancer la production : export MP4 directement prêt à mettre en ligne

Le bouton de bascule "MODE DE PRODUCTION" (en haut de la barre latérale)
permet de passer d'un mode à l'autre ; les réglages d'export (format,
musique, zoom, nom de fichier) sont communs aux deux modes.

## Fonctions générales
- Effet Ken Burns sur les images
- Musique de fond en boucle avec volume réduit
- Sauvegarde et ouverture de projets JSON (les deux modes sont mémorisés)
- Export MP4
- Interface moderne sombre/claire
- Packaging Windows avec installateur et raccourci Bureau

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
Edge TTS nécessite une connexion Internet pour générer les voix (mode "Scènes + texte").
La transcription automatique des sous-titres (mode "Voix off + photos/vidéos")
télécharge un petit modèle de reconnaissance vocale (faster-whisper, modèle
"base", quelques centaines de Mo) lors de sa toute première utilisation :
une connexion Internet est nécessaire ce jour-là ; ensuite, la transcription
fonctionne hors ligne. Choisir "Aucun" pour les sous-titres évite complètement
cette étape.

Le clonage vocal XTTS n'est pas inclus par défaut dans le build Windows afin d'éviter un installateur de plusieurs gigaoctets et des incompatibilités de version. Il peut être ajouté comme module optionnel dans une future version.

### Correction démarrage Windows

Le workflow inclut les métadonnées de `imageio`, `imageio-ffmpeg`, `moviepy`
ainsi que celles du module de reconnaissance vocale (`faster-whisper`,
`ctranslate2`, `tokenizers`, `huggingface_hub`, etc.). MoviePy charge
ImageIO au démarrage et ImageIO recherche sa version via
`importlib.metadata`. Sans ces métadonnées, PyInstaller peut provoquer
`PackageNotFoundError: No package metadata was found for imageio`. Si la
compilation GitHub Actions échoue sur une erreur similaire pour un autre
module, ajoute simplement `--collect-all <module>` et/ou
`--copy-metadata <module>` (nom exact indiqué dans le message d'erreur) à
la commande PyInstaller du workflow.

### Correction : "Production en cours…" qui ne se terminait jamais

**Cause identifiée :** une fois compilée en mode fenêtré (`--windowed`,
sans console) sous Windows, l'application ne dispose plus d'une entrée
standard valide. Les commandes FFmpeg lancées directement par le logiciel
(assemblage final des scènes, mixage de la musique) héritaient alors d'un
handle d'entrée standard invalide et restaient bloquées indéfiniment,
sans jamais produire de fichier ni afficher d'erreur — d'où l'écran
"Production en cours…" figé.

**Correctif appliqué :**
- Un nouveau module `winfix.py`, importé en tout premier par `app.py`,
  force pour **tout** sous-processus lancé par l'application (y compris
  ceux lancés en interne par MoviePy) une entrée standard fermée et
  l'absence de fenêtre de console parasite.
- Les commandes FFmpeg lancées directement par le moteur (`engine.py`)
  utilisent désormais l'option `-nostdin` et une exécution sécurisée
  (`_run_ffmpeg`), qui journalise clairement la sortie FFmpeg en cas
  d'échec au lieu de rester silencieuse.
- Les erreurs réseau (Edge TTS indisponible après 90 secondes) affichent
  désormais un message explicite au lieu de laisser l'utilisateur dans
  l'incertitude.

### Production vidéo
FFmpeg est inclus dans la compilation Windows via imageio-ffmpeg. L'utilisateur final n'a pas besoin d'installer FFmpeg séparément. Edge TTS nécessite Internet pour le mode "Scènes + texte".

La console de production est fixée en bas de la fenêtre et affiche les étapes du rendu. En cas d'erreur, un message détaillé est affiché, avec le journal complet consultable dans la console.
