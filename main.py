import os
import sqlite3
import stripe
from fastapi import FastAPI, Form, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

load_dotenv()
app = FastAPI()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuración de IA (Gemini como respaldo o principal)
client_gemini = None
gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    try:
        from google import genai
        client_gemini = genai.Client(api_key=gemini_api_key)
    except Exception: pass

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ==============================
# LÓGICA DE BÚSQUEDA 3-3-5-1
# ==============================
def query_aura_vault(termino, zip_user=None):
    try:
        conn = sqlite3.connect('aura_brain.db')
        cur = conn.cursor()
        busqueda = f"%{termino.strip().upper()}%"
        
        # 1. TRES LOCALES (Mismo ZIP)
        locales = []
        if zip_user:
            cur.execute("SELECT description, state, zip_code, low_price FROM estimates WHERE (description LIKE ? OR code LIKE ?) AND zip_code = ? ORDER BY low_price ASC LIMIT 3", (busqueda, busqueda, zip_user))
            locales = cur.fetchall()

        # 2. TRES ESTADALES/CONDADO (Mismo Estado, excluyendo los locales ya hallados)
        estadales = []
        if zip_user:
            state_code = zip_user[:2] # Asumiendo prefijo o lógica de estado
            cur.execute("SELECT description, state, zip_code, low_price FROM estimates WHERE (description LIKE ? OR code LIKE ?) AND state = ? AND zip_code != ? ORDER BY low_price ASC LIMIT 3", (busqueda, busqueda, state_code, zip_user))
            estadales = cur.fetchall()

        # 3. CINCO NACIONALES (Los más baratos de todo el país)
        cur.execute("SELECT description, state, zip_code, low_price FROM estimates WHERE (description LIKE ? OR code LIKE ?) ORDER BY low_price ASC LIMIT 5", (busqueda, busqueda))
        nacionales = cur.fetchall()

        # 4. UN PREMIUM (El precio más alto registrado para ese servicio)
        cur.execute("SELECT description, state, zip_code, high_price FROM estimates WHERE (description LIKE ? OR code LIKE ?) ORDER BY high_price DESC LIMIT 1", (busqueda, busqueda))
        premium = cur.fetchone()

        conn.close()
        return {"locales": locales, "estadales": estadales, "nacionales": nacionales, "premium": premium}
    except Exception as e:
        return None

# ==============================
# RUTAS
# ==============================

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):
    datos = query_aura_vault(consulta, zip_user)
    
    # Prompt optimizado para Aura (Asesor Profesional)
    prompt = f"""
    Eres AURA, el sistema experto de May Roga LLC. 
    Tu misión es asesorar al cliente sobre precios médicos/dentales en USA.
    
    ESTRUCTURA OBLIGATORIA DE RESPUESTA:
    1. Menciona que has analizado el mercado para: '{consulta}'.
    2. SECCIÓN LOCAL: Presenta 3 opciones económicas cerca de {zip_user if zip_user else 'su zona'}.
    3. SECCIÓN REGIONAL: Presenta 3 opciones a nivel de estado/condado.
    4. SECCIÓN NACIONAL: Presenta las 5 opciones más baratas detectadas en todo USA.
    5. SECCIÓN PREMIUM: Presenta 1 opción de alto costo (Premium/Concierge).
    
    DATOS OBTENIDOS: {datos}
    IDIOMA: {lang}

    REGLAS:
    - No uses la palabra 'inteligencia artificial' ni 'IA'.
    - No digas 'gobierno'.
    - Usa un tono profesional, interesante y experto.
    - Incluye ventajas de buscar precios bajos.
    - Finaliza con el BLINDAJE LEGAL de May Roga LLC.
    - Al final, invita al cliente a 'ACLARAR DUDAS' si algo no quedó claro.
    """

    # Lógica de generación (OpenAI / Gemini)
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/aclarar-duda")
async def aclarar_duda(pregunta: str = Form(...), contexto: str = Form(...), lang: str = Form("es")):
    # Esta función cumple con el requisito de que el cliente paga por aclarar dudas
    prompt = f"El cliente tiene una duda sobre el reporte anterior. Reporte: {contexto}. Pregunta: {pregunta}. Responde como Aura, asesor de May Roga LLC, de forma profesional y resolutiva."
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    price_ids = {
        "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
        "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
        "special": "price_1SnatfBOA5mT4t0PZouWzfpw"
    }
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_ids[plan.lower()], "quantity": 1}],
            mode="payment",
            success_url="https://aura-by.onrender.com/?success=true",
            cancel_url="https://aura-by.onrender.com/"
        )
        return {"url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
