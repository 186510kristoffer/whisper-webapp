# Whisper Web App & Hardware Cluster

A lightweight, self-hosted web application built with Python and FastAPI. It allows users to record audio directly from their browser or upload existing files and receive fast text transcriptions powered by a local Whisper AI backend.

What makes this project unique is its **hybrid hardware architecture**. The frontend and API are hosted on a Linux server (Lenovo ThinkPad), while the heavy AI inference is offloaded to a smartphone (OnePlus 8T running postmarketOS) connected via a dedicated USB network interface.

## Key Features

*   **Browser-based Recording & Uploads:** Record audio directly from mobile or desktop browsers, or upload standard audio/video files.
*   **FastAPI Backend:** Fast and asynchronous handling of requests.
*   **Hardware-Accelerated Inference:** Forwards optimized audio to a self-hosted `whisper.cpp` server running on a dedicated mobile ARM processor.
*   **Smart Power Management:** The ThinkPad actively monitors the smartphone's thermals and battery via SSH, dynamically toggling USB power using `uhubctl` to keep the battery in a healthy cycle.
*   **Flexible Database Support:** Automatically logs transcription history using SQLAlchemy, supporting SQLite for local development and MariaDB for production environments via environment variables (`.env`).
*   **Auto-formatting:** Uses FFmpeg to ensure audio is dynamically converted to 16kHz mono WAV before inference.
*   **Performance Tracking:** Measures and stores the exact processing time for each transcription.

## System Architecture

1.  **Frontend:** Vanilla JS/HTML/CSS handling media recording and API polling.
2.  **API Gateway (ThinkPad):** A FastAPI service that validates uploads, normalizes audio via FFmpeg, and queues tasks.
3.  **The AI Node (OnePlus 8T):** Connected via USB (RNDIS/Tethering). The FastAPI server wakes the phone up, initiates the `whisper.cpp` server via SSH, and streams the audio payload for processing.
4.  **Telemetry & Daemon:** A background task continually fetches temperature zones (CPU, GPU, Battery) from the smartphone, and controls the USB port power state to prevent battery bloat.
