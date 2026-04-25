# Casa Inteligente — Humberto

Repositorio de backup y documentación de la configuración de Home Assistant + Ring Doorbell.

---

## 🏠 Arquitectura Actual

```
Ring Cloud
    ↓ (push notification)
ring-mqtt (Docker)
    ↓ (MQTT publish)
MQTT Broker (dentro del contenedor de HA)
    ↓ (MQTT subscribe)
Home Assistant
    ↓ (automation + shell_command)
Telegram Bot API
    ↓
Humberto (Telegram)
```

### Componentes

| Componente | Tecnología | Rol |
|---|---|---|
| **Ring Cloud** | SaaS (Amazon) | Detecta motion/ding, genera video de evento |
| **ring-mqtt** | `tsightler/ring-mqtt` (Docker) | Bridge Ring → MQTT. Publica eventos, snapshots y estado en topics MQTT |
| **MQTT Broker** | Mosquitto (dentro del contenedor de HA) | Transporte de eventos entre ring-mqtt y HA |
| **Home Assistant** | `ghcr.io/home-assistant/home-assistant:stable` (Docker) | Automatizaciones, shell commands, notificaciones |
| **Telegram Bot** | `casaha1988bot` (ID: 8609252598) | Envía fotos y mensajes al chat de Humberto |

### Red Docker

Los contenedores corren en la red `casa-inteligente`:
- HA: IP interna `192.168.97.2`
- ring-mqtt: misma red, se conecta a MQTT en `192.168.1.131:1883`
- Externamente HA se accede en `http://192.168.1.131:8123`

---

## 🛏️ Flujo de Eventos

### Motion / Persona detectada

```
Ring detecta motion
  → Ring Cloud genera video del evento
  → ring-mqtt publica en MQTT:
      topic: ring/<location_id>/camera/<device_id>/event_select/attributes
      payload: {"recordingUrl": "https://download-...", "eventId": "..."}
  → HA automation "Ring Motion Notification YAML" se dispara
  → Ejecuta shell_command.ring_get_video_frame
      → curl descarga los primeros ~512KB del video (timeout: 5s)
      → ffmpeg extrae el primer frame del video parcial
      → Guarda en /config/snapshots/ring_motion.jpg
  → telegram_bot.send_photo envía la imagen al chat
  → input_datetime.ring_last_motion se actualiza (cooldown: 60s)
  → input_text.ring_last_event_id se actualiza (deduplicación por eventId)
```

**Ventaja:** La imagen es el **primer frame exacto del video del evento**, no un snapshot tomado después.

### Ding / Timbre

```
Alguien presiona el timbre
  → Ring Cloud notifica
  → ring-mqtt publica:
      topic: ring/.../ding/state → ON
      topic: ring/.../ding/attributes → {"lastDing": ..., "lastDingTime": "..."}
      topic: ring/.../snapshot/image → imagen binaria JPEG (type: "ding")
  → HA automation "Ring Doorbell Notification YAML" se dispara
  → Ejecuta shell_command.ring_get_snapshot
      → Script MQTT pide snapshot on-demand
      → Recibe imagen del topic snapshot/image
      → Guarda en /config/snapshots/ring_ding.jpg
  → telegram_bot.send_photo envía la imagen
  → input_datetime.ring_last_ding se actualiza (cooldown: 180s)
```

**Nota:** El ding actualmente usa snapshot **on-demand** en lugar de esperar el snapshot específico del evento (`type: "ding"`). Esto puede causar que la imagen no corresponda exactamente al momento del timbre. Ver [Pendientes](#-pendientes).

---

## 📁 Estructura del Repositorio

```
.
├── .gitignore              # Excluye runtime files, backups locales
├── README.md               # Este archivo
├── PLAN.md                 # Plan maestro del proyecto
├── homeassistant/
│   ├── configuration.yaml    # Config principal de HA
│   ├── automations.yaml      # Automatizaciones Ring
│   ├── secrets.yaml          # Tokens y credenciales (repo privado)
│   ├── home-assistant_v2.db  # Base de datos completa de HA
│   ├── .storage/             # Estado de integraciones y auth
│   ├── packages/
│   │   └── ring.yaml         # Package de Ring
│   └── scripts/
│       ├── get_ring_snapshot.py    # Snapshot on-demand vía MQTT
│       └── ring_video_frame.py     # Descarga video + extrae frame
└── docs/
    └── SETUP_RING_TELEGRAM.md   # Documentación detallada
```

---

## 🛠️ Disaster Recovery (Restaurar desde cero)

Este repo contiene **todo lo necesario** para reconstruir HA en caso de pérdida total. Incluye `secrets.yaml`, `.storage/`, y `home-assistant_v2.db`.

### Restauración rápida (1 comando)

```bash
# 1. Clonar el repo
git clone https://github.com/hjcg1988/smarthome.git
cd smarthome

# 2. Copiar TODO al contenedor de HA
docker cp homeassistant/. homeassistant:/config/

# 3. Reiniciar
docker restart homeassistant
```

Listo. HA arranca exactamente como estaba — tokens, configuraciones, dispositivos registrados, historial, todo.

---

### Restauración manual (si no tienes el repo clonado)

#### 1. Docker + Docker Compose

Los contenedores se gestionan con Docker. Verificar que estén en la red `casa-inteligente`.

#### 2. Crear directorios en el contenedor de HA

```bash
docker exec homeassistant mkdir -p /config/snapshots /config/scripts /config/packages
```

#### 3. Copiar archivos del repo

```bash
cp -r homeassistant/* ~/homeassistant/
docker cp ~/homeassistant/. homeassistant:/config/
```

#### 4. Reiniciar Home Assistant

```bash
docker restart homeassistant
```

#### 5. Verificar ring-mqtt

```bash
docker logs ring-mqtt --follow
```

Debe mostrar "Connected to MQTT broker" y descubrir la cámara.

---

### ⚠️ Nota de seguridad

Este repo es **privado** y contiene tokens (`secrets.yaml`) + datos de auth (`.storage/`). Mantén 2FA activado en GitHub. Si el repo se ve comprometido, rota tokens inmediatamente.

---

## 📶 Topics MQTT Clave

| Topic | Dirección | Contenido |
|---|---|---|
| `ring/.../event_select/attributes` | ring-mqtt → HA | `{"recordingUrl": "...", "eventId": "..."}` |
| `ring/.../snapshot/image` | ring-mqtt → HA | Imagen JPEG binaria |
| `ring/.../snapshot/attributes` | ring-mqtt → HA | `{"timestamp": ..., "type": "ding" \| "on-demand"}` |
| `ring/.../ding/state` | ring-mqtt → HA | `ON` / `OFF` |
| `ring/.../ding/attributes` | ring-mqtt → HA | `{"lastDing": ..., "lastDingTime": "..."}` |
| `ring/.../take_snapshot/command` | HA → ring-mqtt | `press` (solicita snapshot on-demand) |

---

## 🔧 Troubleshooting

### "No llegan notificaciones a Telegram"

```bash
# Verificar que HA esté corriendo
curl -s http://192.168.1.131:8123/ | head -1

# Ver logs de automatizaciones
docker logs homeassistant --since 10m 2>&1 | grep -i "ring_motion\|ring_ding\|telegram_bot"

# Ver logs de ring-mqtt
docker logs ring-mqtt --since 10m 2>&1 | grep -i "motion\|ding"
```

### "La imagen del motion no corresponde al evento"

Verificar que `configuration.yaml` use `ring_get_video_frame` para motion (no `ring_get_snapshot`):

```yaml
shell_command:
  ring_get_video_frame: "python3 /config/scripts/ring_video_frame.py '{{ url }}' '{{ path }}'"
```

### "La imagen del ding es vieja"

Esto es un [bug conocido](#-pendientes). El ding usa snapshot on-demand. El fix es esperar 2-3 segundos para que ring-mqtt publique el snapshot `type: "ding"` y usar ese en lugar del on-demand.

### "ffmpeg falla con 'Invalid data'"

El video parcial puede estar corrupto. El script ya usa flags tolerantes (`+discardcorrupt`, `ignore_err`). Si persiste, verificar que curl esté descargando algo:

```bash
docker exec homeassistant curl -s -o /tmp/test.mp4 --max-time 5 "<recordingUrl>"
docker exec homeassistant ls -la /tmp/test.mp4
```

---

## 📝 Pendientes

| # | Tarea | Estado |
|---|---|---|
| 1 | **Fix ding:** Esperar snapshot `type: "ding"` en lugar de on-demand | Pendiente |
| 2 | **Cooldowns separados:** `ring_last_motion` (60s) y `ring_last_ding` (180s) | ✅ Hecho |
| 3 | **Backup automático:** Script diario a las 3am + push a GitHub | ✅ Hecho |
| 4 | **Device tracker + geofencing:** Para listas de compra automáticas | Pendiente |
| 5 | **Test delay real:** Medir tiempo end-to-end con evento en vivo | Pendiente |

---

## 📜 Referencias

- [ring-mqtt Documentation](https://github.com/tsightler/ring-mqtt)
- [Home Assistant Telegram Bot](https://www.home-assistant.io/integrations/telegram_bot/)
- [Home Assistant Automation](https://www.home-assistant.io/docs/automation/)

---

*Last updated: 2026-04-24*
