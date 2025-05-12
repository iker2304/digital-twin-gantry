import bpy
import os
import time
import math
import paho.mqtt.client as mqtt

# Configuración MQTT
broker = os.environ.get('MQTT_BROKER', 'mqtt-broker')
port = int(os.environ.get('MQTT_PORT', 1883))

# Conectar al broker MQTT
client = mqtt.Client()
try:
    client.connect(broker, port)
    print(f"Conectado al broker MQTT: {broker}:{port}")
except Exception as e:
    print(f"Error al conectar al broker MQTT: {e}")

# Cargar el modelo .blend (asumiendo que está en /models)
def cargar_modelo():
    # Limpiar la escena actual
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # Buscar archivos .blend en el directorio /models
    model_dir = "/models"
    blend_files = [f for f in os.listdir(model_dir) if f.endswith('.blend')]
    
    if blend_files:
        # Cargar el primer archivo .blend encontrado
        model_path = os.path.join(model_dir, blend_files[0])
        print(f"Cargando modelo: {model_path}")
        
        # Cargar el archivo
        bpy.ops.wm.open_mainfile(filepath=model_path)
        return True
    else:
        print("No se encontraron archivos .blend en /models")
        # Crear un objeto simple para visualización
        bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
        return False

# Configurar la escena para renderizado
def configurar_escena():
    # Configurar el motor de renderizado
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.render.film_transparent = True
    
    # Configurar la resolución
    bpy.context.scene.render.resolution_x = 800
    bpy.context.scene.render.resolution_y = 600
    bpy.context.scene.render.resolution_percentage = 100
    
    # Configurar la calidad (más bajo para renderizado más rápido)
    bpy.context.scene.cycles.samples = 50
    
    # Asegurarse de que hay una cámara
    if 'Camera' not in bpy.data.objects:
        bpy.ops.object.camera_add(location=(10, -10, 10))
        cam = bpy.data.objects['Camera']
        cam.rotation_euler = (math.radians(60), 0, math.radians(45))
    
    # Asegurarse de que hay una luz
    if 'Light' not in bpy.data.objects:
        bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))

# Función para renderizar y guardar la imagen
def renderizar_modelo():
    # Configurar la salida
    output_path = "/app/shared/render.png"
    bpy.context.scene.render.filepath = output_path
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    
    # Renderizar
    bpy.ops.render.render(write_still=True)
    
    print(f"Imagen renderizada guardada en: {output_path}")
    
    # Publicar mensaje MQTT
    try:
        client.publish("gantry/render/updated", output_path)
        print("Notificación enviada por MQTT")
    except Exception as e:
        print(f"Error al publicar mensaje MQTT: {e}")

# Función para actualizar el modelo basado en datos de sensores
def actualizar_modelo(topic, payload):
    # Aquí implementarías la lógica para actualizar el modelo 3D
    # basado en los datos recibidos de los sensores
    print(f"Actualizando modelo con datos: {payload}")
    
    # Ejemplo: mover un objeto basado en la posición de la carreta
    if topic == "gantry/sensors/position":
        try:
            position = float(payload)
            if "Carreta" in bpy.data.objects:
                bpy.data.objects["Carreta"].location.x = position
        except:
            pass

# Callback para mensajes MQTT recibidos
def on_message(client, userdata, msg):
    print(f"Mensaje recibido: {msg.topic} {msg.payload.decode()}")
    actualizar_modelo(msg.topic, msg.payload.decode())

# Configurar callback MQTT
client.on_message = on_message
client.subscribe("gantry/sensors/#")
client.loop_start()

# Función principal
def main():
    # Cargar el modelo
    cargar_modelo()
    
    # Configurar la escena
    configurar_escena()
    
    # Bucle principal
    try:
        while True:
            # Renderizar el modelo
            renderizar_modelo()
            
            # Esperar antes de la siguiente actualización
            time.sleep(10)
    except KeyboardInterrupt:
        print("Proceso interrumpido por el usuario")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    # Esperar un momento para que el broker MQTT esté disponible
    time.sleep(5)
    main()