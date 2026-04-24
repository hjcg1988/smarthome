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
  → input_datetime.ring_last_notification se actualiza (cooldown: 180s)
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
  → input_datetime.ring_last_notification se actualiza
```

**Nota:** El ding actualmente usa snapshot **on-demand** en lugar de esperar el snapshot específico del evento (`type: "ding"`). Esto puede causar que la imagen no corresponda exactamente al momento del timbre. Ver [Pendientes](#-pendientes).

---

## 📁 Estructura del Repositorio

```
.
├── .gitignore              # Excluye secrets, DBs, runtime files
├── README.md               # Este archivo
├── homeassistant/
│   ├── configuration.yaml    # Config principal de HA
│   ├── automations.yaml      # Automatizaciones Ring
│   ├── packages/
│   │   ″ ring.yaml           # Package de Ring (actualmente vacío)
│   ″ scripts/
│       ├── get_ring_snapshot.py    # Snapshot on-demand vía MQTT
│       ″ ring_video_frame.py     # Descarga video + extrae frame
″ docs/
    ″ SETUP_RING_TELEGRAM.md   # Documentación detallada
```

---

## 🛠️ Requisitos para Restaurar

### 1. Docker + Docker Compose

Los contenedores se gestionan con Docker. Verificar que estén en la red `casa-inteligente`.

### 2. Archivos que NO están en este repo (manuales)

| Archivo | Ubicación en host | Cómo obtener |
|---|---|---|
| `secrets.yaml` | `~/homeassistant/secrets.yaml` | Contiene tokens de Ring, MQTT, Telegram. **NUNCA subir a git.** Reconstruir manualmente desde backup seguro. |
| Token de ring-mqtt | Variable `RINGMQTT_TOKEN` o config.json | Obtener de `https://github.com/tsightler/ring-mqtt` (autenticación Ring). |
| Token de Telegram Bot | `secrets.yaml` → `telegram_bot` | Obtener de [@BotFather](https://t.me/BotFather). |

### 3. Crear directorios en el contenedor de HA

```bash
docker exec homeassistant mkdir -p /config/snapshots /config/scripts
```

### 4. Copiar archivos

```bash
cp configuration.yaml automations.yaml ~/homeassistant/
cp scripts/*.py ~/homeassistant/scripts/
chmod +x ~/homeassistant/scripts/*.py
docker cp ~/homeassistant/scripts/*.py homeassistant:/config/scripts/
```

### 5. Configurar `secrets.yaml`

Ejemplo de estructura mínima:

```yaml
# ~/homeassistant/secrets.yaml
telegram_bot_api_key: "YOUR_BOT_TOKEN"
```

Y en `configuration.yaml` referenciarlo si es necesario (actualmente el chat_id está hardcodeado en config).

### 6. Reiniciar Home Assistant

```bash
docker restart homeassistant
```

### 7. Verificar ring-mqtt

```bash
docker logs ring-mqtt --follow
```

Debe mostrar "Connected to MQTT broker" y descubrir la cámara.

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

| # | Tarea | Prioridad |
|---|---|---|
| 1 | **Fix ding:** Esperar snapshot `type: "ding"` en lugar de on-demand | Alta |
| 2 | **Separar cooldowns:** Crear `ring_last_ding` y `ring_last_motion` como entidades independientes | Media |
| 3 | **Test delay real:** Medir tiempo end-to-end con evento en vivo | Media |
| 4 | **Range requests:** Si Ring algún día soporta HTTP Range, optimizar a descarga de ~200KB | Baja |

---

## 📜 Referencias

- [ring-mqtt Documentation](https://github.com/tsightler/ring-mqtt)
- [Home Assistant Telegram Bot](https://www.home-assistant.io/integrations/telegram_bot/)
- [Home Assistant Automation](https://www.home-assistant.io/docs/automation/)

---

*Last updated: 2026-04-24*
