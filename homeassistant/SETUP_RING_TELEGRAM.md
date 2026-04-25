# Ring Doorbell → Telegram Notifications

## 📋 Última actualización: 2026-04-24

## Arquitectura

```
Ring Cloud → ring-mqtt (Docker) → MQTT → Home Assistant → Telegram Bot → Humberto
```

## Contenedores Docker

| Contenedor | Imagen | IP |
|---|---|---|
| homeassistant | ghcr.io/home-assistant/home-assistant:stable | 192.168.97.2 |
| ring-mqtt | tsightler/ring-mqtt | Orch (comparte red con HA) |

## Configuración MQTT

- **Broker**: `192.168.1.131:1883` (dentro del contenedor de HA se ve como `192.168.97.2`)
- ring-mqtt publica en: `ring/<location_id>/camera/<device_id>/...`

## Topics clave de ring-mqtt

| Topic | Contenido |
|---|---|
| `.../event_select/attributes` | JSON con `recordingUrl` del evento |
| `.../snapshot/image` | Imagen binaria JPEG |
| `.../snapshot/attributes` | JSON con `timestamp` y `type` (ding/on-demand) |
| `.../ding/state` | ON/OFF cuando suena el timbre |
| `.../ding/attributes` | `lastDing`, `lastDingTime` |
| `.../info/state` | Stream RTSP, batería, señal WiFi |

## Scripts

### `/config/scripts/get_ring_snapshot.py`
Pide snapshot on-demand vía MQTT. Usado por la automatización de **ding**.

### `/config/scripts/ring_video_frame.py` ⭐ NUEVO
Descarga el video del evento desde `recordingUrl`, extrae el primer frame con `ffmpeg`.

**Optimizaciones:**
- Usa `curl` (C) en lugar de `urllib` (Python) → más rápido
- Timeout de descarga: **5 segundos** → corta temprano, solo necesita primer GOP
- ffmpeg tolerante a archivos incompletos (`+discardcorrupt`, `ignore_err`)

## Automatizaciones

### Motion (`automations.yaml`)

```yaml
trigger: MQTT topic event_select/attributes
action:
  1. shell_command.ring_get_video_frame → descarga video + extrae frame
  2. telegram_bot.send_photo → envía imagen
  3. input_datetime.set_datetime → actualiza cooldown
```

**Cooldown**: 180 segundos (compartido con ding)

### Ding (`automations.yaml`)

```yaml
trigger: binary_sensor.front_door_ding attribute lastDing cambia
action:
  1. shell_command.ring_get_snapshot → snapshot on-demand vía MQTT
  2. telegram_bot.send_photo → envía imagen
  3. input_datetime.set_datetime → actualiza cooldown
```

## ⚠️ Problemas conocidos

### 1. Ding usa snapshot on-demand (no el del evento)
Cuando suena el timbre, ring-mqtt publica DOS snapshots:
- `type: "on-demand"` → llega primero (~1s)
- `type: "ding"` → llega después (~2s), es la imagen REAL del evento

El script `get_ring_snapshot.py` toma el primero que llega (on-demand), que puede no ser del momento exacto del ding.

**Fix pendiente**: Modificar la automatización de ding para esperar 2-3 segundos y usar el snapshot `type: "ding"`.

### 2. Cooldown compartido entre motion y ding
Si suena el timbre y 10 segundos después hay motion, el motion se bloquea por cooldown.

**Fix pendiente**: Crear entidades separadas (`ring_last_ding`, `ring_last_motion`).

### 3. Imagen "vieja" en ding
El snapshot on-demand se toma 1-2 segundos después del evento. Si la persona ya se fue, la foto no corresponde.

**Fix aplicado**: Motion ahora usa frame del video → imagen exacta del momento del evento.

## Delay estimado

| Evento | Delay total |
|---|---|
| Motion | ~2.5-6 segundos (antes ~6-8s) |
| Ding | ~3-6 segundos |

**Optimización motion**: Script ahora tarda ~0.5-1.0s en lugar de ~1.4s.

## Logs útiles

```bash
# Ver eventos de ring-mqtt
docker logs ring-mqtt --since 10m 2>&1 | grep -i "motion\|ding\|snapshot"

# Ver automatizaciones de HA
docker logs homeassistant --since 10m 2>&1 | grep -i "ring_motion\|ring_ding\|telegram_bot"

# Ver si HA está corriendo
curl -s http://192.168.1.131:8123/ | head -1
```

## Archivos de config

| Archivo | Rol |
|---|---|
| `~/homeassistant/configuration.yaml` | Config principal + shell_commands + logger |
| `~/homeassistant/automations.yaml` | Automatizaciones motion + ding |
| `~/homeassistant/scripts/get_ring_snapshot.py` | Snapshot on-demand vía MQTT |
| `~/homeassistant/scripts/ring_video_frame.py` | Frame del video del evento |
| `~/homeassistant/secrets.yaml` | Tokens (NO versionar) |
| `~/homeassistant/packages/ring.yaml` | Vacío — todo en configuration.yaml |

## Backup automático

Los archivos `.bak` se crean antes de cada modificación:
- `configuration.yaml.bak`
- `automations.yaml.bak`

## Próximos pasos

1. ✅ Motion usa frame del video → imagen exacta
2. ⏳ Probar delay real con evento en vivo
3. 🔧 Fix ding para esperar snapshot `type: "ding"` → imagen real del timbre
4. 🔧 Separar cooldowns de motion y ding
