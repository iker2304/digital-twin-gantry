from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
import os
from typing import Optional
import paho.mqtt.client as mqtt
from fastapi.staticfiles import StaticFiles

# Configuración de seguridad
SECRET_KEY = "tu_clave_secreta_aqui"  # En producción, usa una clave segura y guárdala como variable de entorno
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Modelos de datos
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

# Base de datos simulada de usuarios (en producción, usa una base de datos real)
fake_users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        "disabled": False,
    }
}

# Configuración de seguridad
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

# Configuración de plantillas y archivos estáticos
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Añadir esta línea aquí
app.mount("/shared", StaticFiles(directory="/app/shared"), name="shared")

# Funciones de autenticación
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Rutas de la aplicación
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    print(f"Intento de inicio de sesión: {username}/{password}")
    
    # Autenticación simplificada para depuración
    if username == "admin" and password == "una_contraseña_más_segura":
        # Redirigir directamente sin token
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    else:
        print(f"Intento de inicio de sesión fallido: {username}/{password}")
        return templates.TemplateResponse("login.html", {"request": request, "error": "Usuario o contraseña incorrectos"})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Datos de ejemplo
    digital_twin_data = {
        "estado": "activo",
        "deformacion": "2.3 mm",
        "carga": "150 N",
        "posicion_carreta": "45 cm",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "user": {"username": "admin"}, "data": digital_twin_data}
    )

# API para obtener datos del gemelo digital (para uso por aplicaciones cliente)
@app.get("/api/twin-data")
async def get_twin_data(current_user: User = Depends(get_current_active_user)):
    # Aquí obtendrías datos reales del gemelo digital
    return {
        "estado": "activo",
        "deformacion": "2.3 mm",
        "carga": "150 N",
        "posicion_carreta": "45 cm",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# Configuración MQTT
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print("Conectado al broker MQTT")
    client.subscribe("gantry/render/updated")

def on_message(client, userdata, msg):
    print(f"Mensaje recibido: {msg.topic} {msg.payload}")
    # Aquí puedes actualizar alguna variable global o base de datos
    # para indicar que hay una nueva imagen disponible

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("mqtt-broker", 1883)
mqtt_client.loop_start()

# Montar el directorio compartido como estático para servir las imágenes
app.mount("/shared", StaticFiles(directory="/app/shared"), name="shared")