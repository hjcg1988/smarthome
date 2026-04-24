# 🏠 Plan Maestro: Casa Inteligente - Estado Actual

**Última actualización:** 2026-04-24
**Servidor:** Mac Mini M4 Pro (192.168.1.131)
**Repo:** https://github.com/hjcg1988/smarthome

---

## Arquitectura Actual (2026-04-24)

```
Ring Doorbell → Ring Cloud → ring-mqtt → MQTT (Mosquitto) → Home Assistant → Telegram
```

**Flujo motion/person:**
```
Ring detecta motion → Ring Cloud genera video del evento
  → ring-mqtt publica recordingUrl en MQTT
  → HA automation ejecuta ring_video_frame.py
    → curl descarga primeros ~500KB del video (timeout 5s)
    → ffmpeg extrae primer frame
  → telegram_bot.send_photo envía imagen a Humberto
```

**Flujo ding:**
```
Alguien presiona timbre → ring-mqtt publica snapshot
  → HA automation ejecuta get_ring_snapshot.py (snapshot on-demand)
  → telegram_bot.send_photo envía imagen
```

## Containers Docker activos

| Container | Puerto | Network | Comando para levantar |
|---|---|---|---|
| **homeassistant** | 8123 | OrbStack | Ya estaba corriendo, se levanta solo |
| **mosquitto** | 1883 | host | `docker start mosquitto` |
| **ring-mqtt** | 55123 (web) | host | `docker start ring-mqtt` |

### Containers detenidos (no necesarios para Plan A)

| Container | Razón |
|---|---|
| frigate | No necesario. Ring no soporta RTSP continuo |
| compreface | No funciona en ARM64 (TensorFlow sin AVX) |
| apple-silicon-detector | Pendiente optimización (funciona con CoreML pero ZMQ falla) |

### Directorios de configuración

```
~/casa-inteligente/
├── mosquitto/
│   ├── config/mosquitto.conf
│   ├── data/
│   └── log/
├── ring-mqtt/
│   ├── config.json
│   └── ring-state.json  ← TOKEN DE RING AQUÍ
├── frigate/
│   ├── config.yml
│   ├── model_cache/yolov9-t-320.onnx
│   └── storage/
├── apple-silicon-detector/  ← Clonado de GitHub, con venv de Python
└── homeassistant/
    └── packages/ring.yaml
```

---

## ✅ Completado (7/8 pasos)

1. ✅ Red Docker `casa-inteligente` + directorios base
2. ✅ Mosquitto (MQTT broker) en puerto 1883
3. ✅ Frigate 0.17 instalado (detenido, no necesario para Plan A)
4. ✅ Apple Silicon Detector compilado (pendiente debug ZMQ con Frigate)
5. ✅ Ring-MQTT conectado a Ring Doorbell "Front Door" (Chula Vista)
   - Device ID: `5c475e011b89`
   - Location ID: `98b21b5e-8d1e-4240-a98a-d71e7ebac30d`
   - Batería: 97%, WiFi: -49 a -71 dBM
6. ✅ Home Assistant configurado:
   - MQTT integration conectada a 192.168.1.131:1883
   - Telegram bot configurado (token en secrets.yaml, chat_id: 8514988238)
   - Automatizaciones Ring en `automations.yaml`:
     - `Ring Motion Notification YAML` → Telegram con foto del video del evento
     - `Ring Doorbell Notification YAML` → Telegram con snapshot
     - `input_boolean.ring_silence` → modo silencio
7. ✅ **Optimizaciones motion (2026-04-24):**
   - Motion usa frame del video del evento (`recordingUrl`) en lugar de snapshot on-demand
   - Script `ring_video_frame.py`: curl 5s timeout + ffmpeg tolerante a archivos incompletos
   - Deduplicación por `eventId` (input_text.ring_last_event_id) evita notificaciones duplicadas
   - Delay estimado: ~2.5-6 segundos vs ~6-8 segundos anterior
   - Todo documentado en repo GitHub + README.md

---

## ⏳ Pendiente (pasos restantes)

### Paso 7: Device Tracker (presencia)

**Qué hacer:**
1. Instalar Home Assistant Companion App en celulares (Humberto + esposa)
2. Configurar device tracker en HA
3. Crear zonas en HA para tiendas (Costco, tienda mexicana, etc.)
4. Usar el skill `mandado` para las listas de compras

**Configuración de zonas (agregar a configuration.yaml o packages):**
```yaml
zone:
  - name: Costco
    latitude: <coordenadas_reales>
    longitude: <coordenadas_reales>
    radius: 200
    icon: mdi:store
  - name: TiendaMexicana
    latitude: <coordenadas_reales>
    longitude: <coordenadas_reales>
    radius: 100
    icon: mdi:store
```

**Automatización de presencia:**
```yaml
automation:
  - alias: "Esposa llegó a casa"
    trigger:
      - platform: zone
        entity_id: device_tracker.esposa_telefono
        zone: zone.home
        event: enter
    action:
      - service: notify.telegram
        data:
          message: "🏠 Tu esposa acaba de llegar"
```

### Paso 8: Lista de mandado al llegar a tiendas

**Qué hacer:**
1. Usar el skill `mandado` para gestionar listas en MEMORY.md
2. Crear helpers en HA para las listas
3. Automatización: al entrar a zona de tienda → enviar lista por Telegram

**Automatización:**
```yaml
automation:
  - alias: "Lista de mandado al llegar a Costco"
    trigger:
      - platform: zone
        entity_id: device_tracker.humberto_telefono
        zone: zone.costco
        event: enter
    action:
      - service: notify.telegram
        data:
          message: >
            🛒 ¡Llegaste a Costco!
            📋 Pendientes:
            (lista de items pendientes)
```

### 🔧 Mejoras pendientes de Ring (no bloqueantes)

| # | Tarea | Prioridad | Notas |
|---|---|---|---|
| 1 | **Fix ding:** Esperar snapshot `type: "ding"` en lugar de on-demand | Alta | On-demand llega primero pero no es la imagen exacta del evento |
| 2 | **Separar cooldowns:** `ring_last_ding` y `ring_last_motion` independientes | Media | Actualmente comparten cooldown de 180s |
| 3 | **Range requests:** Si Ring soporta HTTP Range, descargar ~200KB | Baja | Actualmente no soporta (devuelve 400) |
| 4 | **Optimizar script:** ffmpeg pipe desde curl sin archivo temporal | Baja | Reduce I/O en disco |

---

## Decisión de diseño: Plan A (Ring simplificado)

**Por qué:** Las cámaras Ring NO soportan streaming RTSP continuo. El stream solo se activa temporalmente bajo demanda (motion/ding).

**Plan A = Solo notificaciones de motion/ding via Ring → MQTT → HA → Telegram**

**Lo que SÍ funciona:**
- ✅ Notificación de motion con foto
- ✅ Notificación de ding (alguien en la puerta) con foto
- ✅ Modo silencio desde Telegram
- ✅ Device tracker para presencia
- ✅ Lista de mandado al llegar a tiendas

**Lo que NO funciona con Ring (Plan A):**
- ❌ Detección continua de objetos (personas, carros, paquetes)
- ❌ Grabación 24/7
- ❌ Reconocimiento facial (Frigate necesita stream continuo)
- ❌ Detección de paquetes dejados sin timbre

**Para agregar detección continua en el futuro:**
- Comprar cámara IP con RTSP nativo (Reolink ~$30-50)
- Configurar Frigate con esa cámara
- Ring sigue como timbre, cámara RTSP para vigilancia

---

## Troubleshooting

### Si ring-mqtt se cae:
```bash
docker start ring-mqtt
docker logs ring-mqtt  # verificar conexión
```

### Si HA pierde conexión MQTT:
1. Ir a http://192.168.1.131:8123
2. Settings → Devices & Services → MQTT → Reconfigure

### Si no llegan notificaciones Telegram:
1. Verificar que el bot token sigue válido en secrets.yaml
2. Verificar que `input_boolean.ring_silence` está OFF
3. Verificar logs: `docker logs homeassistant | grep telegram`

### Reiniciar todo:
```bash
docker restart mosquitto ring-mqtt homeassistant
```
