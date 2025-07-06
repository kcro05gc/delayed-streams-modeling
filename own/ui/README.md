# DSM Test Interface

Interface minimale pour tester les modèles STT (Speech-to-Text) et TTS (Text-to-Speech) du projet Delayed Streams Modeling.

## Utilisation

### Lancement du serveur backend (REQUIS)
```bash
cd own/ui
uv run server.py
# Le serveur démarre sur http://localhost:8888
```

Ou avec Python standard :
```bash
cd own/ui
pip install flask flask-cors
python server.py
```

## Fonctionnalités

### Text-to-Speech (TTS)
- Saisie manuelle de texte ou sélection de fichiers de test pré-remplis
- Génération des commandes pour exécuter la synthèse vocale
- 10 fichiers de test variés (anglais, français, poésie, technique, etc.)

### Speech-to-Text (STT)
- Sélection de fichiers audio existants
- Choix entre modèles anglais (2.6B) ou anglais+français (1B)
- Affichage des commandes pour la transcription

## Structure
- `index.html` : Interface principale
- `styles.css` : Styles responsive
- `script.js` : Logique de l'application
- `README.md` : Ce fichier

## Nouvelles fonctionnalités

Le serveur backend permet maintenant de :
- **Générer et lire directement les fichiers audio TTS** dans le navigateur
- **Transcrire automatiquement les fichiers audio STT** avec affichage des résultats
- **Enregistrer audio en direct** depuis le microphone
- **Téléverser des fichiers MP3/WAV/OGG** pour transcription
- **Traitement automatique des fichiers longs** (>10min) par segments de 5 minutes
- **Charger dynamiquement les fichiers de test**
- **Sauvegarder les fichiers audio générés** dans le dossier `generated_audio/`

## Architecture
- `server.py` : Serveur Flask qui exécute les modèles et sert les fichiers
- `index.html` : Interface principale
- `styles.css` : Styles responsive avec animations
- `script.js` : Communication avec le backend via API REST
- `generated_audio/` : Dossier créé automatiquement pour stocker les fichiers audio générés

## API Endpoints
- `POST /api/tts` : Génère un fichier audio à partir de texte
- `POST /api/stt` : Transcrit un fichier audio
- `POST /api/stt-upload` : Transcrit un fichier audio téléversé
- `GET /api/test-file/<filename>` : Charge un fichier de test
- `GET /audio/<filename>` : Sert les fichiers audio générés
- `POST /api/cleanup` : Nettoie les fichiers audio générés

## Gestion des fichiers longs

Pour les fichiers audio de plus de 10 minutes :
- Le système les découpe automatiquement en segments de 5 minutes
- Chaque segment est transcrit séparément  
- Les résultats sont combinés avec timestamps (format [MM:SS])
- Cela évite les crashes de mémoire avec les très longs fichiers
- Le temps de traitement est proportionnel à la durée du fichier

**Exemple de transcription segmentée :**
```
[00:00] Début de la première partie...

[05:00] Début de la deuxième partie...

[10:00] Début de la troisième partie...
```