Whisper Web App
A lightweight web application built with Python and FastAPI. It allows users to record audio directly from their browser and receive text transcriptions.

The backend automatically formats the audio using FFmpeg and sends it to a self-hosted Whisper API endpoint. All transcriptions are saved locally in an SQLite database for easy access to the transcription history.

Key Features:

 - Browser-based Recording: Record audio directly from mobile or desktop browsers.

 - FastAPI Backend: Fast and asynchronous handling of requests.

 - Whisper AI Integration: Forwards audio to a dedicated Whisper server for fast inference.

 - SQLite Database: Automatically logs the language and text of every transcription using SQLAlchemy.

 - Auto-formatting: Uses FFmpeg to ensure the audio is always converted to 16kHz mono WAV before inference.
