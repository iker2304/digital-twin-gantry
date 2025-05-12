import paho.mqtt.client as mqtt
import json
import time
import random
import os

# Obtener la configuración del broker MQTT desde variables de entorno
broker = os.environ.get('MQTT_BROKER', 'mqtt-broker')
port = int(os.environ.get('MQTT_PORT', 1883))

client = mqtt.Client()
try:
    client.connect(broker, port, 60)
    print(f"Conectado al broker MQTT: {broker}:{port}")
except Exception as e:
    print(f"Error al conectar al broker MQTT: {e}")

while True:
    data = {
        "x": random.uniform(0, 5),
        "y": random.uniform(0, 1),
        "z": random.uniform(0, 5)
    }
    # Publicar en el mismo tema que está escuchando el visualizador
    client.publish("auv/twin/position", json.dumps(data))
    print("Datos enviados:", data)
    time.sleep(1)