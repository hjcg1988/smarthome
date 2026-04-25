#!/bin/bash
# Home Assistant Daily Backup Script
# Runs at 3:00 AM daily via cron
# Backs up HA config to smarthome-repo and pushes to GitHub

set -euo pipefail

HA_DIR="$HOME/homeassistant"
REPO_DIR="$HOME/smarthome-repo"
BACKUP_DIR="$REPO_DIR/homeassistant"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

echo "[$TIMESTAMP] Starting HA backup..."

# Ensure repo exists
if [ ! -d "$REPO_DIR/.git" ]; then
    echo "ERROR: Git repo not found at $REPO_DIR"
    exit 1
fi

# Copy config files (excluding sensitive/cache dirs)
rsync -av --delete \
    --exclude='.storage/' \
    --exclude='.cloud/' \
    --exclude='.cache/' \
    --exclude='*.bak*' \
    --exclude='.DS_Store' \
    --exclude='.HA_VERSION' \
    --exclude='.ha_run.lock' \
    --exclude='home-assistant.log*' \
    --exclude='custom_components/' \
    --exclude='__pycache__/' \
    --exclude='.git/' \
    "$HA_DIR/" "$BACKUP_DIR/"

# Add timestamp note
echo "# Last backup: $TIMESTAMP" > "$BACKUP_DIR/.backup-timestamp"

cd "$REPO_DIR"

# Check if there are changes
if git diff --quiet && git diff --staged --quiet; then
    echo "[$TIMESTAMP] No changes to commit."
    exit 0
fi

# Commit and push
git add -A
git commit -m "HA auto-backup: $TIMESTAMP" || true
git push origin main

echo "[$TIMESTAMP] Backup completed and pushed to GitHub."
