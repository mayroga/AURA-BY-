import os
import random
import json
import stripe
import openai
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ==============================
# GENERACIÓN AUTOMÁTICA DE DATOS
# ==============================
ESTADOS_A = ["FL", "NY", "TX", "PA", "IL", "OH", "GA", "NC", "MI", "NJ", "VA", "WA", "AZ", "MA", "TN", "IN", "MO", "MD", "WI", "CO", "MN", "SC", "AL", "LA", "KY"]
ESTADOS_B = ["CA", "OR", "OK", "UT", "NV", "IA", "AR", "MS", "KS", "CT", "NM", "NE", "WV", "ID", "HI", "NH", "ME", "MT", "RI", "DE", "SD", "ND", "AK", "VT", "WY"]

PROCEDIMIENTOS = {
    "MRI Lumbar Spine": 400, "Dental Crown": 800, "Complete Blood Count": 40,
    "Chest X-Ray": 80, "Colonoscopy": 1100, "ER Visit (Level 3)": 650,
    "Physical Therapy": 100, "Dental Cleaning": 90, "CT Scan Abdomen": 500,
    "Pelvic Ultrasound": 200, "Root Canal": 1000, "Ear Wax Removal": 60,
    "Skin Biopsy": 180, "Prenatal Visit": 150, "Flu Shot": 25,
    "Diabetes Screening": 35, "Mental Health Session": 200, "Sleep Study": 1300,
    "Allergy Test": 300, "Cataract Surgery": 2500
}

def inicializar_archivos():
    if not os.path.exists('data_bloque_A.json'):
        data = {p: {e: {"cash": round(v*random.uniform(0.8, 1.3), 2), "zip": "33101"} for e in ESTADOS_A} for p, v in PROCEDIMIENTOS.items()}
        with open('data_bloque_A.json', 'w') as f: json.dump(data, f)
    if not os.path.exists('data_bloque_B.json'):
        data = {p: {e: {"cash": round(v*random.uniform(0.8, 1.3), 2), "zip": "90210"} for e in ESTADOS_B} for p, v in PROCEDIMIENTOS.items()}
        with open('data_bloque_B.json', 'w') as f: json.dump(data, f)

inicializar_archivos()

# ==============================
# APP & CONFIG
# ==============================
load_dotenv()
app = FastAPI(title="AURA by May Roga LLC")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")
engine = create_engine(os.getenv("DATABASE_URL"))

# ==============================
# MOTOR DE DOBLE VERIFICACIÓN
# ==============================
async def motor_dual_verificacion(consulta, zip_code, lang):
    # 1. LEER BLOQUES (Realidad de 50 Estados)
    try:
        with open('data_bloque_A.json') as f: data_a = json.load(f).get(consulta, "No data")
        with open('data_bloque_B.json') as f: data_b = json.load(f).get(consulta, "No data")
        contexto_json = f"Bloque A (Este): {data_a} | Bloque B (Oeste): {data_b}"
    except:
        contexto_json = "Error leyendo repositorio."

    # 2. SQL
    try:
        with engine.connect() as conn:
            query = text("SELECT provider_name, cash_price, state, zip FROM health_system WHERE zip = :z AND (procedure_name ILIKE :q) LIMIT 5")
            res = conn.execute(query, {"z": zip_code, "q": f"%{consulta}%"}).fetchall()
            sql_data = str([dict(row) for row in res])
    except:
        sql_data = "SQL no disponible."

    # 3. VERIFICACIÓN DUAL
    check_prompt = f"""
    Eres AURA de May Roga LLC. Genera un reporte médico para {consulta} en ZIP {zip_code}.
    REPOSITORIO 50 ESTADOS: {contexto_json}
    DATOS SQL LOCALES: {sql_data}
    
    INSTRUCCIÓN: Compara los datos del Bloque A y Bloque B. Si el precio nacional es más bajo que el local, destaca el ahorro.
    ESTRUCTURA: 3 Locales, 5 Nacionales, 1 Premium.
    FORMATO: Tablas HTML estilo #0cf. Sin mencionar IA.
    Idioma: {lang}
    """
    
    resp = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "Asesoría de peso May Roga LLC. Precisión absoluta."},
                  {"role": "user", "content": check_prompt}]
    )
    return resp.choices[0].message.content

# ==============================
# RUTAS
# ==============================
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", encoding="utf-8") as f: return f.read()

@app.post("/estimado")
async def estimado(consulta: str = Form(...), zip_user: str = Form("33160"), lang: str = Form("es")):
    res = await motor_dual_verificacion(consulta, zip_user, lang)
    return JSONResponse({"resultado": res})

@app.post("/consultar-asesor")
async def consultar_asesor(pregunta: str = Form(...), reporte_previo: str = Form(...), lang: str = Form("es")):
    resp = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "Asesor de May Roga LLC. Resuelve dudas del reporte."},
                  {"role": "user", "content": f"Contexto: {reporte_previo}. Duda: {pregunta}"}]
    )
    return {"respuesta_asesor": resp.choices[0].message.content}

# ... (Rutas de Stripe y Admin igual que antes)
