import bpy
import os
import time
import math
import paho.mqtt.client as mqtt
import json

# Limpiar la escena actual
bpy.ops.wm.read_factory_settings(use_empty=True)

# Configuración MQTT
broker = os.environ.get('MQTT_BROKER', 'mqtt-broker')
port = int(os.environ.get('MQTT_PORT', 1883))

# Variables globales para almacenar datos de sensores
sensor_data = {
    "x": 0,
    "y": 0,
    "z": 0
}

# Conectar al broker MQTT
client = mqtt.Client()
try:
    client.connect(broker, port)
    print(f"Conectado al broker MQTT: {broker}:{port}")
except Exception as e:
    print(f"Error al conectar al broker MQTT: {e}")

# Función para cargar el modelo .blend
def cargar_modelo():
    # Buscar archivos .blend en el directorio /models
    model_dir = "/models"
    print(f"Buscando archivos .blend en: {model_dir}")
    
    try:
        # Listar todos los archivos en el directorio
        todos_archivos = os.listdir(model_dir)
        print(f"Archivos encontrados en {model_dir}: {todos_archivos}")
        
        # Filtrar solo los archivos .blend
        blend_files = [f for f in todos_archivos if f.endswith('.blend')]
        print(f"Archivos .blend encontrados: {blend_files}")
        
        if blend_files:
            # Cargar el primer archivo .blend encontrado
            model_path = os.path.join(model_dir, blend_files[0])
            print(f"Intentando cargar modelo: {model_path}")
            
            try:
                # Cargar el archivo
                bpy.ops.wm.open_mainfile(filepath=model_path)
                print(f"Modelo cargado exitosamente: {model_path}")
                
                # Listar objetos en la escena
                print("Objetos en la escena:")
                for obj in bpy.data.objects:
                    print(f" - {obj.name} (tipo: {obj.type})")
                
                return True
            except Exception as e:
                print(f"Error al cargar el modelo {model_path}: {e}")
                # Crear un objeto simple para visualización
                bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
                return False
        else:
            print("No se encontraron archivos .blend en /models")
            # Crear un objeto simple para visualización
            bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
            return False
    except Exception as e:
        print(f"Error al listar archivos en {model_dir}: {e}")
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

# Función para actualizar el modelo basado en datos de sensores
def actualizar_modelo():
    # Obtener el primer objeto de la escena que no sea cámara o luz
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            # Actualizar la posición del objeto según los datos del sensor
            obj.location.x = sensor_data["x"]
            obj.location.y = sensor_data["y"]
            obj.location.z = sensor_data["z"]
            print(f"Objeto {obj.name} actualizado a posición: {sensor_data}")
            break

# Función para renderizar y guardar la imagen
def renderizar_modelo():
    # Configurar la salida
    output_path = "/app/shared/render.png"
    bpy.context.scene.render.filepath = output_path
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    
    # Renderizar
    bpy.ops.render.render(write_still=True)
    
    print(f"Imagen renderizada guardada en: {output_path}")

# Callback para mensajes MQTT recibidos
def on_message(client, userdata, msg):
    global sensor_data
    print(f"Mensaje recibido: {msg.topic} {msg.payload.decode()}")
    
    try:
        # Actualizar datos de sensores
        if msg.topic == "auv/twin/position" or msg.topic == "gantry/sensors/position":
            sensor_data = json.loads(msg.payload.decode())
            print(f"Datos de sensores actualizados: {sensor_data}")
    except Exception as e:
        print(f"Error al procesar mensaje MQTT: {e}")

# Configurar callback MQTT
client.on_message = on_message
client.subscribe("auv/twin/position")
client.subscribe("gantry/sensors/position")
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
            # Actualizar el modelo con los datos de los sensores
            actualizar_modelo()
            
            # Renderizar el modelo
            renderizar_modelo()
            
            # Esperar antes de la siguiente actualización
            time.sleep(5)
    except KeyboardInterrupt:
        print("Proceso interrumpido por el usuario")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    # Esperar un momento para que el broker MQTT esté disponible
    time.sleep(5)
    main()