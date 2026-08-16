# Whisper Web App

website: https://transcriber.kristoffer-server.uk/

A lightweight, self-hosted web application built with Python and FastAPI. It allows users to record audio directly from their browser or upload existing files and receive fast text transcriptions powered by a local Whisper AI backend.

The backend automatically formats incoming audio using FFmpeg and proxies it to a dedicated, hardware-accelerated Whisper server. All transcriptions, including language settings, text, and processing duration, are securely logged via SQLAlchemy.

## Key Features

- **Browser-based Recording & Uploads:** Record audio directly from mobile or desktop browsers, or upload standard audio/video files.
- **FastAPI Backend:** Fast and asynchronous handling of requests.
- **Whisper AI Integration:** Forwards optimized audio to a self-hosted `whisper.cpp` server running on dedicated hardware (e.g., via USB network interface).
- **Flexible Database Support (SQLite / MariaDB):** Automatically logs transcription history using SQLAlchemy, supporting SQLite for local development and MariaDB for production environments via environment variables (`.env`).
- **Performance Tracking:** Measures and stores the exact processing time for each transcription.
- **Auto-formatting:** Uses FFmpeg to ensure audio is dynamically converted to 16kHz mono WAV before inference.
