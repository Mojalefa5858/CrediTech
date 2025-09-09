#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install system dependencies
apt-get update
apt-get install -y tesseract-ocr libtesseract-dev libleptonica-dev pkg-config

# Install Python dependencies
pip install -r requirements.txt
