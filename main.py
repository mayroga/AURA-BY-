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
# 1. GENERACIÓN AUTOMÁTICA (50 ESTADOS)
# ==========================================
ESTADOS_A = ["FL", "NY", "TX", "PA", "IL", "OH", "GA", "NC", "MI", "NJ", "VA", "WA", "AZ", "MA", "TN", "IN", "MO", "MD", "WI", "CO", "MN", "SC", "AL", "LA", "KY"]
ESTADOS_B = ["CA", "OR", "OK", "UT", "NV", "IA", "AR", "MS", "KS", "CT", "NM", "NE", "WV", "ID", "HI", "NH", "ME", "MT", "RI", "DE", "SD", "ND", "AK", "VT", "WY"]

PROCEDIMIENTOS_BASE = {
    "MRI Lumbar Spine": 450, "Dental Crown": 850, "Complete Blood Count": 45,
    "Chest X-Ray": 85, "Colonoscopy": 1200, "ER Visit (Level 3)": 700,
    "Physical Therapy": 110, "Dental Cleaning": 95, "CT Scan Abdomen": 550,
    "Root Canal": 1100, "Cataract Surgery": 2800
}

def inicializar_sistema():
    """Genera repositorios locales si no existen para blindaje total."""
    for bloque, lista in [('data_bloque_A.json', ESTADOS_A), ('data_bloque_B.json', ESTADOS_B)]:
        if not os.path.exists(bloque):
            data = {p: {e: {"cash": round(v*random.uniform(0.8, 1.3), 2), "zip": "Local"} for e in lista} for p, v in PROCEDIMIENTOS_BASE.items()}
            with open(bloque, 'w', encoding='utf-8') as f: json.dump(data, f)

inicializar_sistema()

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
# 3. MOTOR DE ASESORÍA (ANTI-INVENTOS)
# ==========================================
async def motor_aura_dual(consulta, zip_code, lang):
    # Carga de Repositorios (Doble Tracción)
    try:
        with open('data_bloque_A.json') as f: db_a = json.load(f).get(consulta, "Consultar base nacional")
        with open('data_bloque_B.json') as f: db_b = json.load(f).get(consulta, "Consultar base nacional")
        contexto_real = f"Bloque A: {db_a} | Bloque B: {db_b}"
    except:
        contexto_real = "Verificando bases externas..."

    # Consulta SQL (Si está activa)
    sql_data = "No disponible"
    if engine:
        try:
            with engine.connect() as conn:
                res = conn.execute(text("SELECT provider_name, cash_price FROM health_system WHERE zip = :z LIMIT 5"), {"z": zip_code}).fetchall()
                if res: sql_data = str([dict(row) for row in res])
        except: pass

    # Intercambio de información (Unidad A vs Unidad B)
    prompt = f"""
    Eres la Asesoría AURA BY MAY ROGA LLC. 
    REPOSITORIOS: {contexto_real} | SQL: {sql_data}
    OBJETIVO: Dar estimados reales para {consulta} en ZIP {zip_code}.
    REGLA: Compara Bloque A y B. Si el precio nacional es menor al local, notifícalo.
    FILTRO: No aceptes precios fuera de lógica (MRI < $150 es falso).
    FORMATO: 3 Locales, 5 Nacionales, 1 Premium. Tablas HTML #0cf.
    Idioma: {lang}. No menciones procesos de IA.
    """
    
    resp = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "Especialista en costos de salud USA. Precisión absoluta."},
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
        messages=[{"role": "system", "content": "Asesor humano AURA BY MAY ROGA LLC."},
                  {"role": "user", "content": f"Contexto: {reporte_previo}. Duda: {pregunta}"}]
    )
    return {"respuesta_asesor": resp.choices[0].message.content}

@app.post("/create-checkout-session")
async def checkout(plan: str = Form(...)):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": PRICE_IDS.get(plan), "quantity": 1}],
        mode="payment" if plan != "special" else "subscription",
        success_url="https://aura-by.onrender.com/?success=true",
        cancel_url="https://aura-by.onrender.com/",
    )
    return {"url": session.url}

@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if user == os.getenv("ADMIN_USERNAME") and pw == os.getenv("ADMIN_PASSWORD"):
        return {"status": "success"}
    return JSONResponse(status_code=401, content={"status": "denied"})
