import os
import sqlite3
import stripe
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Configuración de Llaves
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Variables de Acceso Admin (Render)
ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin_default")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "pass_default")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ==============================
# LÓGICA DE BÚSQUEDA 3-3-5-1
# ==============================
def query_aura_vault(termino, zip_user=None):
    try:
        conn = sqlite3.connect('aura_brain.db')
        cur = conn.cursor()
        busqueda = f"%{termino.strip().upper()}%"
        
        # 3 LOCALES (Mismo ZIP)
        locales = []
        if zip_user:
            cur.execute("SELECT description, state, zip_code, low_price FROM estimates WHERE (description LIKE ? OR code LIKE ?) AND zip_code = ? ORDER BY low_price ASC LIMIT 3", (busqueda, busqueda, zip_user))
            locales = cur.fetchall()

        # 3 REGIONALES (Mismo Estado/Condado)
        regionales = []
        if zip_user:
            state_prefix = zip_user[:2]
            cur.execute("SELECT description, state, zip_code, low_price FROM estimates WHERE (description LIKE ? OR code LIKE ?) AND state LIKE ? AND zip_code != ? ORDER BY low_price ASC LIMIT 3", (busqueda, busqueda, f"{state_prefix}%", zip_user))
            regionales = cur.fetchall()

        # 5 NACIONALES (Más baratos de USA)
        cur.execute("SELECT description, state, zip_code, low_price FROM estimates WHERE (description LIKE ? OR code LIKE ?) ORDER BY low_price ASC LIMIT 5", (busqueda, busqueda))
        nacionales = cur.fetchall()

        # 1 PREMIUM (Precio más alto)
        cur.execute("SELECT description, state, zip_code, high_price FROM estimates WHERE (description LIKE ? OR code LIKE ?) ORDER BY high_price DESC LIMIT 1", (busqueda, busqueda))
        premium = cur.fetchone()

        conn.close()
        return {"locales": locales, "regionales": regionales, "nacionales": nacionales, "premium": premium}
    except:
        return None

# ==============================
# RUTAS DE ACCESO Y ESTIMADOS
# ==============================

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    # Esta es la parte que restaura tu acceso gratuito
    if user == ADMIN_USER and pw == ADMIN_PASS:
        return {"status": "success", "message": "Acceso gratuito concedido."}
    return JSONResponse(status_code=401, content={"status": "error", "message": "Credenciales incorrectas."})

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):
    datos = query_aura_vault(consulta, zip_user)
    idiomas = {"es": "Español", "en": "English", "ht": "Haitian Creole"}
    
    prompt = f"""
    Eres AURA de May Roga LLC. Asesor profesional de precios médicos/dentales.
    REPORTE PARA: {consulta} en {zip_user if zip_user else 'USA'}.
    IDIOMA: {idiomas.get(lang, 'Español')}

    DATOS ENCONTRADOS (ESTRUCTURA 3-3-5-1):
    - Locales: {datos['locales'] if datos else 'No hay datos exactos'}
    - Regionales: {datos['regionales'] if datos else 'No hay datos'}
    - Nacionales: {datos['nacionales'] if datos else 'No hay datos'}
    - Premium: {datos['premium'] if datos else 'No hay datos'}

    INSTRUCCIONES:
    1. Presenta los 3 precios locales, los 3 regionales, los 5 nacionales más baratos y el premium de forma clara.
    2. Resalta la consulta del usuario en negrita.
    3. Usa un tono experto. No menciones "IA" ni "Gobierno".
    4. Incluye ventajas/desventajas y el BLINDAJE LEGAL de May Roga LLC al final.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/aclarar-duda")
async def aclarar_duda(pregunta: str = Form(...), contexto: str = Form(...), lang: str = Form("es")):
    # Los clientes que pagan tienen derecho a preguntar
    prompt = f"Como Aura de May Roga LLC, resuelve esta duda del cliente basándote en su reporte anterior. Reporte: {contexto}. Duda: {pregunta}."
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    # IDs de precios de tu Stripe
    PRICE_IDS = {"rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq", "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE", "special": "price_1SnatfBOA5mT4t0PZouWzfpw"}
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_IDS[plan.lower()], "quantity": 1}],
            mode="payment",
            success_url="https://aura-by.onrender.com/?success=true",
            cancel_url="https://aura-by.onrender.com/"
        )
        return {"url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
