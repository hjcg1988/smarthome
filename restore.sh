#!/bin/bash
# Disaster Recovery Script for Humberto's Smart Home
# Restores Home Assistant + Ring + Mosquitto from this repo

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
HA_HOST_DIR="$HOME/homeassistant"
INFRA_DIR="$HOME/casa-inteligente"

echo "🛠️  Starting full restore from $REPO_DIR"

# 1. Create directories
echo "📁  Creating directories..."
mkdir -p "$HA_HOST_DIR"
mkdir -p "$INFRA_DIR/ring-mqtt"
mkdir -p "$INFRA_DIR/mosquitto/config"
mkdir -p "$INFRA_DIR/mosquitto/data"
mkdir -p "$INFRA_DIR/mosquitto/log"

# 2. Copy HA config
echo "📤  Copying Home Assistant config..."
rsync -av --delete "$REPO_DIR/homeassistant/" "$HA_HOST_DIR/"

# 3. Copy infrastructure configs
echo "📤  Copying Mosquitto and Ring-MQTT configs..."
rsync -av --delete "$REPO_DIR/infrastructure/mosquitto/config/" "$INFRA_DIR/mosquitto/config/"
rsync -av --delete "$REPO_DIR/infrastructure/ring-mqtt/" "$INFRA_DIR/ring-mqtt/"

# 4. Create Docker network if it doesn't exist
echo "🔗  Creating Docker network 'casa-inteligente'..."
docker network create casa-inteligente 2>/dev/null || echo "Network already exists"

# 5. Start services with docker-compose
echo "🚀  Starting services with docker-compose..."
cd "$REPO_DIR"
docker-compose up -d

echo ""
echo "✅  Restore complete!"
echo ""
echo "Services starting up:"
echo "  - Home Assistant: http://192.168.1.131:8123"
echo "  - Mosquitto MQTT: 192.168.1.131:1883"
echo "  - Ring-MQTT:      host network"
echo ""
echo "Check logs:"
echo "  docker logs homeassistant --follow"
echo "  docker logs ring-mqtt --follow"
echo "  docker logs mosquitto --follow"
