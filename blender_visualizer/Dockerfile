FROM linuxserver/blender:latest

WORKDIR /app
COPY scripts/ /app/
COPY models/ /models/

RUN mkdir -p /app/shared

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Crear y activar entorno virtual
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalar paho-mqtt en el entorno virtual
RUN pip3 install paho-mqtt

# Comando para ejecutar el script de renderizado
CMD ["blender", "--background", "--python", "render.py"]