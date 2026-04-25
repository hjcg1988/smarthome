# Disaster Recovery Guide — Casa Inteligente

> **Para:** Cualquier agente AI o persona que necesite reconstruir todo desde cero.
> **Tiempo estimado:** 15-30 minutos.

---

## 🚨 Contexto Rápido

- **Máquina:** Mac Mini M4 Pro (macOS)
- **IP:** 192.168.1.131
- **Docker:** Instalado y corriendo
- **Servicios:** Home Assistant + Mosquitto MQTT + Ring-MQTT
- **Notificaciones:** Telegram bot `@casaha1988bot`, chat_id `8514988238`
- **Repo privado:** `github.com/hjcg1988/smarthome` (contiene tokens y credenciales)

---

## 📋 Checklist Pre-Restore

Antes de empezar, asegurar que existen:
- [ ] Docker Desktop instalado y corriendo
- [ ] Git instalado
- [ ] Acceso al repo privado `hjcg1988/smarthome` (con `secrets.yaml` y `.storage/`)
- [ ] Conexión a internet (para descargar imágenes de Docker)

---

## 🚀 Restauración Completa (Modo Automático)

### Paso 1: Clonar el repo

```bash
cd ~
git clone https://github.com/hjcg1988/smarthome.git
cd smarthome
```

### Paso 2: Ejecutar el script de restore

```bash
./restore.sh
```

Este script hace TODO automáticamente:
1. Crea directorios locales (`~/homeassistant`, `~/casa-inteligente`)
2. Copia config de HA, Mosquitto y Ring-MQTT
3. Crea la red Docker `casa-inteligente`
4. Arranca los 3 contenedores con `docker-compose up -d`

### Paso 3: Verificar que todo arrancó

```bash
# Ver contenedores corriendo
docker ps

# Ver logs de cada servicio
docker logs homeassistant --since 1m
docker logs ring-mqtt --since 1m
docker logs mosquitto --since 1m
```

### Paso 4: Probar notificaciones

Abrir HA en `http://192.168.1.131:8123` → Developer Tools → Services →
llamar `telegram_bot.send_message` con:
- `message: "Restore test — Casa Inteligente OK"`
- `target: 8514988238`

---

## 🔧 Restauración Manual (Si el script falla)

### Paso 1: Directorios locales

```bash
mkdir -p ~/homeassistant
mkdir -p ~/casa-inteligente/ring-mqtt
mkdir -p ~/casa-inteligente/mosquitto/config
mkdir -p ~/casa-inteligente/mosquitto/data
mkdir -p ~/casa-inteligente/mosquitto/log
```

### Paso 2: Copiar configuraciones

```bash
cd ~/smarthome

# Home Assistant config
rsync -av homeassistant/ ~/homeassistant/

# Mosquitto config
cp -r infrastructure/mosquitto/config/* ~/casa-inteligente/mosquitto/config/

# Ring-MQTT config
cp infrastructure/ring-mqtt/config.json ~/casa-inteligente/ring-mqtt/
cp infrastructure/ring-mqtt/ring-state.json ~/casa-inteligente/ring-mqtt/
```

### Paso 3: Crear red Docker

```bash
docker network create casa-inteligente 2>/dev/null || true
```

### Paso 4: Iniciar contenedores

```bash
cd ~/smarthome
docker-compose up -d
```

### Paso 5: Esperar y verificar

- Home Assistant: `http://192.168.1.131:8123` (toma ~30-60s en arrancar)
- Mosquitto: `192.168.1.131:1883`
- ring-mqtt: Verificar logs que diga "Connected to MQTT broker"

---

## 🗺️ Arquitectura de Red

```
┌─────────────────────────────────────────────────────────────┐
│                      Mac Mini M4 Pro                        │
│                     192.168.1.131                           │
│                                                             │
│  ┌─────────────────┐   ┌──────────────┐  ┌─────────────┐   │
│  │  Home Assistant │   │   Mosquitto  │  │  ring-mqtt  │   │
│  │   (host net)    │◄──┤  (bridge)    │◄─┤  (host net) │   │
│  │   :8123         │   │  :1883       │  │             │   │
│  └────────┬────────┘   └──────────────┘  └──────┬──────┘   │
│           │                                      │          │
│           │      shell_command + automation      │          │
│           │                                      │          │
│           ▼                                      ▼          │
│       snapshots/                            Ring Cloud      │
│       ring_motion.jpg                            │          │
│       ring_ding.jpg                              │          │
│                                                  │          │
└──────────────────────────────────────────────────┼──────────┘
                                                   │
                                                   ▼
                                        ┌──────────────────┐
                                        │  Telegram API    │
                                        │  @casaha1988bot  │
                                        │  chat: 8514988238│
                                        └──────────────────┘
```

---

## 📁 Archivos Críticos en el Repo

| Archivo | Para qué sirve | Peligro si se pierde |
|---|---|---|
| `homeassistant/secrets.yaml` | Tokens de Telegram, Ring, etc. | Hay que reconfigurar TODOS los tokens manualmente |
| `homeassistant/.storage/` | Auth, device trackers, integraciones | Hay que re-autenticar todo de nuevo |
| `homeassistant/home-assistant_v2.db` | Historial completo de sensores | Se pierde todo el historial |
| `infrastructure/ring-mqtt/config.json` | Config de ring-mqtt | Hay que reconfigurar Ring de cero |
| `infrastructure/ring-mqtt/ring-state.json` | Token de refresh de Ring | Ring deja de funcionar hasta re-login |
| `infrastructure/mosquitto/config/` | Config del broker MQTT | MQTT deja de funcionar |
| `docker-compose.yaml` | Definición de servicios | Hay que reconstruir contenedores manualmente |

---

## 🔄 Backup Automático

Un cron job corre diariamente a las 3:00 AM:

```bash
0 3 * * * ~/smarthome-repo/scripts/backup-ha.sh
```

Este script:
1. Copia `~/homeassistant/` → `~/smarthome-repo/homeassistant/`
2. Hace commit con timestamp
3. Hace push a GitHub

Para restaurar desde el backup más reciente, simplemente hacer `git pull` y ejecutar `./restore.sh`.

---

## ⚠️ Problemas Conocidos y Soluciones

### "No llegan notificaciones de Ring"

1. Verificar que ring-mqtt esté conectado:
   ```bash
   docker logs ring-mqtt --since 5m | grep -i "connected\|error"
   ```
2. Verificar que HA vea los topics MQTT:
   ```bash
   docker exec mosquitto mosquitto_sub -t "ring/#" -v
   ```
3. Verificar que la automatización esté activa en HA

### "La imagen del ding es vieja/stale"

Esto es un bug pendiente. El ding usa snapshot on-demand en lugar del snapshot del evento. Ver `PLAN.md` para el fix planeado.

### "El motion no envía imagen"

1. Verificar que `ffmpeg` y `curl` funcionan dentro del contenedor de HA:
   ```bash
   docker exec homeassistant ffmpeg -version | head -1
   docker exec homeassistant curl --version | head -1
   ```
2. Verificar que existe el script:
   ```bash
   docker exec homeassistant ls -la /config/scripts/ring_video_frame.py
   ```

---

## 📞 Contactos Útiles

| Entidad | Valor |
|---|---|
| Telegram bot | `@casaha1988bot` |
| Telegram chat_id | `8514988238` |
| Ring device_id | `98b21b5e-8d1e-4240-a98a-d71e7ebac30d` |
| Ring camera_id | `5c475e011b89` |

---

## ✅ Post-Restore Checklist

Después del restore, verificar:
- [ ] HA carga en `http://192.168.1.131:8123`
- [ ] ring-mqtt logs muestran "Connected to MQTT broker"
- [ ] Mosquitto acepta conexiones en puerto 1883
- [ ] Automatizaciones están activas (Settings → Automations → Show 2 active)
- [ ] Test de Telegram: Developer Tools → Services → telegram_bot.send_message
- [ ] Test de Ring: Generar un evento de movimiento y verificar que llega a Telegram

---

*Last updated: 2026-04-24*
*Author: Jarvis (Engineer Owl)*
