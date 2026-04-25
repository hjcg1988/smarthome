# Casa Inteligente — Humberto

Repositorio privado de backup y documentación para Home Assistant + Ring + Mosquitto.

> ⚠️ **Este repo contiene tokens y credenciales.** Es privado, mantén 2FA activado en GitHub.

---

## 🏠 Arquitectura

```
Ring Cloud → ring-mqtt → Mosquitto → Home Assistant → Telegram
```

| Componente | Tecnología | Rol |
|---|---|---|
| **Ring Cloud** | SaaS | Detecta motion/ding, genera video |
| **ring-mqtt** | Docker (`tsightler/ring-mqtt`) | Bridge Ring → MQTT |
| **Mosquitto** | Docker (`eclipse-mosquitto`) | Broker MQTT |
| **Home Assistant** | Docker (`home-assistant:stable`) | Automatizaciones y notificaciones |
| **Telegram** | Bot `@casaha1988bot` | Alertas con imagen al chat `8514988238` |

**Red:** `casa-inteligente` (bridge para Mosquitto, host para HA y ring-mqtt).  
**HA:** `http://192.168.1.131:8123`

---

## 🚀 Restore desde cero

```bash
git clone https://github.com/hjcg1988/smarthome.git
cd smarthome
./restore.sh
```

Ver guía completa en [`DR.md`](DR.md).

---

## 📁 Estructura

```
.
├── docker-compose.yaml       # Definición de los 3 servicios
├── restore.sh                # 1 comando para reconstruir todo
├── DR.md                     # Guía de Disaster Recovery completa
├── PLAN.md                   # Plan maestro y pendientes
├── scripts/
│   └── backup-ha.sh          # Backup automático diario (3:00 AM)
├── homeassistant/            # Config completa de HA
│   ├── configuration.yaml
│   ├── automations.yaml
│   ├── secrets.yaml          # Tokens (DR — repo privado)
│   ├── home-assistant_v2.db  # Base de datos completa
│   ├── .storage/             # Auth e integraciones
│   └── scripts/
│       ├── ring_video_frame.py     # Motion: extrae frame de video
│       └── get_ring_snapshot.py    # Ding: snapshot on-demand
├── infrastructure/
│   ├── mosquitto/config/     # Config del broker
│   └── ring-mqtt/            # Config + refresh token de Ring
└── docs/
    └── SETUP_RING_TELEGRAM.md    # Documentación detallada del setup
```

---

## 🔄 Backup

Automático todos los días a las 3:00 AM vía cron:

```bash
crontab -l | grep backup-ha
# 0 3 * * * ~/smarthome-repo/scripts/backup-ha.sh
```

Backup manual:
```bash
./scripts/backup-ha.sh
```

---

## 📜 Documentación

| Archivo | Contenido |
|---|---|
| [`DR.md`](DR.md) | Restore paso a paso, troubleshooting, contactos |
| [`PLAN.md`](PLAN.md) | Plan maestro, arquitectura, pendientes |
| [`docs/SETUP_RING_TELEGRAM.md`](docs/SETUP_RING_TELEGRAM.md) | Cómo funciona la integración Ring → Telegram |

---

*Last updated: 2026-04-24*
