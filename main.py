import os
import json
import random
import stripe
import openai
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ==========================================
# 1. INICIALIZACIÓN DE REPOSITORIOS (50 ESTADOS)
# ==========================================
ESTADOS_A = ["FL", "NY", "TX", "PA", "IL", "OH", "GA", "NC", "MI", "NJ", "VA", "WA", "AZ", "MA", "TN", "IN", "MO", "MD", "WI", "CO", "MN", "SC", "AL", "LA", "KY"]
ESTADOS_B = ["CA", "OR", "OK", "UT", "NV", "IA", "AR", "MS", "KS", "CT", "NM", "NE", "WV", "ID", "HI", "NH", "ME", "MT", "RI", "DE", "SD", "ND", "AK", "VT", "WY"]

PROCEDIMIENTOS_BASE = {
    "MRI Lumbar Spine": 450, "Dental Crown": 850, "Complete Blood Count": 45,
    "Chest X-Ray": 85, "Colonoscopy": 1200, "ER Visit (Level 3)": 700,
    "Physical Therapy": 110, "Dental Cleaning": 95, "CT Scan Abdomen": 550,
    "Root Canal": 1100, "Cataract Surgery": 2800
}

def inicializar_archivos():
    # Bloque A
    if not os.path.exists('data_bloque_A.json'):
        data = {p: {e: {"cash": round(v*random.uniform(0.8, 1.2), 2), "zip": "33101"} for e in ESTADOS_A} for p, v in PROCEDIMIENTOS_BASE.items()}
        with open('data_bloque_A.json', 'w') as f: json.dump(data, f)
    # Bloque B
    if not os.path.exists('data_bloque_B.json'):
        data = {p: {e: {"cash": round(v*random.uniform(0.8, 1.2), 2), "zip": "90210"} for e in ESTADOS_B} for p, v in PROCEDIMIENTOS_BASE.items()}
        with open('data_bloque_B.json', 'w') as f: json.dump(data, f)

inicializar_archivos()

# ==========================================
# 2. CONFIGURACIÓN CORE
# ==========================================
load_dotenv()
app = FastAPI(title="AURA BY MAY ROGA LLC")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

try:
    engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
except:
    engine = None

PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw"
}

# ==========================================
# 3. MOTOR DE ASESORÍA DUAL (ANTI-INVENTOS)
# ==========================================
async def motor_aura_dual(consulta, zip_code, lang):
    # Carga de Repositorios y Tabla de Ley
    try:
        with open('referencia_medicare.json', 'r') as f: ley = json.load(f).get(consulta, "Referencia general")
        with open('data_bloque_A.json', 'r') as f: b_a = json.load(f).get(consulta, {})
        with open('data_bloque_B.json', 'r') as f: b_b = json.load(f).get(consulta, {})
    except:
        ley, b_a, b_b = "N/A", {}, {}

    # Consulta SQL
    sql_data = "No disponible"
    if engine:
        try:
            with engine.connect() as conn:
                res = conn.execute(text("SELECT provider_name, cash_price, state FROM health_system WHERE zip = :z LIMIT 5"), {"z": zip_code}).fetchall()
                if res: sql_data = str([dict(row) for row in res])
        except: pass

    prompt = f"""
    SISTEMA AURA BY MAY ROGA LLC. 
    REPOSITORIOS: Bloque A: {b_a} | Bloque B: {b_b}
    TABLA LEY MEDICARE/MEDICAID: {ley}
    DATOS SQL LOCALES: {sql_data}

    TAREA: Generar reporte médico para {consulta} en ZIP {zip_code}.
    1. Compara Bloque A y B. Si el precio nacional es menor al local, destaca el ahorro.
    2. Usa la Tabla Ley como ancla para que los precios no sean inventados.
    3. ESTRUCTURA: Tabla HTML con 3 Locales, 5 Nacionales (más baratos), 1 Premium.
    4. ESTILO: Borde #0cf, fondo oscuro, texto blanco. No menciones IA.
    Idioma: {lang}.
    """
    
    resp = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "Asesoría Profesional May Roga LLC. Precisión de 50 estados."},
                  {"role": "user", "content": prompt}],
        temperature=0
    )
    return resp.choices[0].message.content

# ==========================================
# 4. RUTAS OPERATIVAS
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", encoding="utf-8") as f: return f.read()

@app.post("/estimado")
async def estimado(consulta: str = Form(...), zip_user: str = Form("33160"), lang: str = Form("es")):
    resultado = await motor_aura_dual(consulta, zip_user, lang)
    return JSONResponse({"resultado": resultado})

@app.post("/consultar-asesor")
async def consultar_asesor(pregunta: str = Form(...), reporte_previo: str = Form(...)):
    resp = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "Asesor Humano AURA BY MAY ROGA LLC. Resuelve dudas del reporte."},
                  {"role": "user", "content": f"Contexto: {reporte_previo}. Pregunta: {pregunta}"}]
    )
    return {"respuesta_asesor": resp.choices[0].message.content}

@app.post("/create-checkout-session")
async def checkout(plan: str = Form(...)):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_IDS.get(plan), "quantity": 1}],
            mode="payment" if plan != "special" else "subscription",
            success_url="https://aura-by.onrender.com/?success=true",
            cancel_url="https://aura-by.onrender.com/",
        )
        return {"url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if user == os.getenv("ADMIN_USERNAME") and pw == os.getenv("ADMIN_PASSWORD"):
        return {"status": "success"}
    return JSONResponse(status_code=401, content={"status": "denied"})
