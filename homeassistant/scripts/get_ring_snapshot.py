#!/usr/local/bin/python3
import paho.mqtt.client as mqtt
import sys
import time

MQTT_BROKER = "192.168.97.2"
MQTT_PORT = 1883
TOPIC_IMAGE = "ring/98b21b5e-8d1e-4240-a98a-d71e7ebac30d/camera/5c475e011b89/snapshot/image"
TOPIC_ATTR = "ring/98b21b5e-8d1e-4240-a98a-d71e7ebac30d/camera/5c475e011b89/snapshot/attributes"
TOPIC_CMD = "ring/98b21b5e-8d1e-4240-a98a-d71e7ebac30d/camera/5c475e011b89/take_snapshot/command"

output_file = sys.argv[1] if len(sys.argv) > 1 else "/config/snapshots/ring_snapshot.jpg"
received = {"image": None, "attr": None}
connected = False


def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        connected = True
        client.subscribe(TOPIC_IMAGE)
        client.subscribe(TOPIC_ATTR)
    else:
        print(f"Connect failed with code {rc}", file=sys.stderr)
        sys.exit(1)


def on_message(client, userdata, msg):
    if msg.topic == TOPIC_IMAGE:
        received["image"] = msg.payload
    elif msg.topic == TOPIC_ATTR:
        received["attr"] = msg.payload.decode()

    if received["image"] is not None and received["attr"] is not None:
        with open(output_file, "wb") as f:
            f.write(received["image"])
        print(f"Saved snapshot to {output_file} ({len(received['image'])} bytes)")
        print(f"Attributes: {received['attr']}")
        client.disconnect()


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 5)
client.loop_start()

# Wait for connection
start = time.time()
while not connected and (time.time() - start) < 5:
    time.sleep(0.1)

if not connected:
    print("ERROR: Could not connect to MQTT", file=sys.stderr)
    sys.exit(1)

# Publish snapshot command
time.sleep(0.3)
client.publish(TOPIC_CMD, "press")

# Wait for both image and attributes
start = time.time()
while (received["image"] is None or received["attr"] is None) and (time.time() - start) < 15:
    time.sleep(0.1)

client.loop_stop()

if received["image"] is None:
    print("ERROR: No image received", file=sys.stderr)
    sys.exit(1)
if received["attr"] is None:
    print("WARNING: No attributes received", file=sys.stderr)

sys.exit(0)
