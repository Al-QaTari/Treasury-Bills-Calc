#!/bin/bash

# Make the directory for playwright browsers and change ownership
mkdir -p /home/appuser/.cache/ms-playwright
chown -R appuser:appuser /home/appuser/.cache/ms-playwright

# Run the playwright install command as the appuser
sudo -u appuser python -m playwright install chromium
