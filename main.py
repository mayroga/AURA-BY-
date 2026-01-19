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

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

# IDs de Stripe (Price IDs reales)
PRICE_IDS = {
    "rapido": "price_1QisFhL8uXJ8YwO6pLp", # EJEMPLO - Reemplaza con los tuyos
    "standard": "price_1QisFhL8uXJ8YwO6pLq",
    "special": "price_1QisFhL8uXJ8YwO6pLr",
    "donacion": "https://buy.stripe.com/28E00igMD8dR00v5vl7Vm0h"
}

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def query_aura_brain(termino, zip_user):
    try:
        conn = sqlite3.connect('aura_brain.db')
        cur = conn.cursor()
        b = f"%{termino.upper()}%"
        
        # Lógica 3-3-3-5-1
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE description LIKE ? AND zip_code = ? LIMIT 3", (b, zip_user))
        locales = cur.fetchall()
        
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE description LIKE ? AND zip_code LIKE ? LIMIT 3", (b, f"{zip_user[:3]}%"))
        condado = cur.fetchall()

        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE description LIKE ? ORDER BY low_price ASC LIMIT 5", (b,))
        nacionales = cur.fetchall()
        
        conn.close()
        return {"locales": locales, "condado": condado, "nacionales": nacionales}
    except: return None

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):
    datos_sql = query_aura_brain(consulta, zip_user)
    
    # PROMPT DE AUTORIDAD MÁXIMA
    prompt = f"""
    ERES AURA BY MAY ROGA LLC. EXPERTO AGENTE DE MEDICARE, MEDICAID Y PRECIOS DE SALUD EN USA.
    TU OBJETIVO: Dar transparencia absoluta sobre el costo estimado.
    
    DATOS SQL: {datos_sql}
    CONSULTA: {consulta} | ZIP: {zip_user} | IDIOMA: {lang}

    MANDATO CRÍTICO:
    1. Si los datos SQL están vacíos o son inconsistentes con la realidad legal (Medicare Fee Schedule), TOMA EL MANDO. Usa tu conocimiento de experto en FAIR Health, United Health Care y CMS para dar el estimado real.
    2. ESTRUCTURA 3-3-3-5-1: 3 locales, 3 condado, 3 estado, 5 nacionales (ahorro máximo) y 1 premium.
    3. Muestra el precio CASH vs Precio Estimado con Seguro.
    4. TONO: Profesional, Autoridad, Agente del Gobierno (en función). No digas 'IA'.
    5. BLINDAJE LEGAL: Inclúyelo al final de la respuesta.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    if plan == "donacion": return {"url": PRICE_IDS["donacion"]}
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": PRICE_IDS[plan], "quantity": 1}],
        mode="payment",
        success_url="https://tu-url.com/?success=true",
        cancel_url="https://tu-url.com/"
    )
    return {"url": session.url}

@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if user == os.getenv("ADMIN_USERNAME") and pw == os.getenv("ADMIN_PASSWORD"):
        return {"status": "ok"}
    return JSONResponse(status_code=401)

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f: return f.read()
