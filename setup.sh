#!/bin/bash
set -e

# Check system deps
for cmd in ffmpeg ffprobe mpv node npm; do
    command -v $cmd >/dev/null 2>&1 || { echo "$cmd not found. Install it."; exit 1; }
done

# Python
pip install -e .

# Remotion
cd remotion && npm install

echo "Ready. Run: videvide script.yaml"
