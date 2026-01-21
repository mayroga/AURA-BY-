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

PRICE_IDS = {
    "rapido": "price_1QisFhL8uXJ8YwO6pLp",
    "standard": "price_1QisFhL8uXJ8YwO6pLq",
    "special": "price_1QisFhL8uXJ8YwO6pLr",
    "donacion": "https://buy.stripe.com/28E00igMD8dR00v5vl7Vm0h"
}

def query_aura_brain(termino, zip_user):
    conn = sqlite3.connect('aura_brain.db')
    cur = conn.cursor()
    b = f"%{termino.upper()}%"
    
    # 3 Locales
    cur.execute("SELECT zip_code, county, state, low_price FROM prices WHERE (description LIKE ? OR cpt_code LIKE ?) AND zip_code = ? LIMIT 3", (b, b, zip_user))
    locales = cur.fetchall()
    
    # 3 Condado/Estado
    cur.execute("SELECT zip_code, county, state, low_price FROM prices WHERE (description LIKE ? OR cpt_code LIKE ?) AND state = (SELECT state FROM prices WHERE zip_code = ? LIMIT 1) LIMIT 3", (b, b, zip_user))
    estado = cur.fetchall()

    # 5 Nacionales (Ahorro Máximo)
    cur.execute("SELECT zip_code, county, state, low_price FROM prices WHERE (description LIKE ? OR cpt_code LIKE ?) ORDER BY low_price ASC LIMIT 5", (b, b))
    nacionales = cur.fetchall()
    
    conn.close()
    return {"locales": locales, "estado": estado, "nacionales": nacionales}

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):
    datos = query_aura_brain(consulta, zip_user)
    
    prompt = f"""
    ERES AURA BY MAY ROGA LLC. ASESOR PROFESIONAL DE COSTOS MÉDICOS.
    CONVIERTE ESTOS DATOS EN TABLAS HTML LIMPIAS Y PROFESIONALES.
    
    DATOS: {datos}
    CONSULTA: {consulta} | ZIP USUARIO: {zip_user}

    REGLAS DE RESPUESTA:
    1. USA TABLAS HTML con bordes celestes.
    2. ESTRUCTURA: 
       - Tabla 1: "3 Opciones Locales (Zip {zip_user})"
       - Tabla 2: "3 Opciones Regionales (Condado/Estado)"
       - Tabla 3: "5 Opciones de Máximo Ahorro Nacional" (Muestra Zip, Condado y Estado)
       - Sección 4: "1 Opción Premium de Referencia"
    3. CONTENIDO: Precio Cash vs Estimado con Seguro (Usa CMS/Fair Health).
    4. EXPLICACIONES: Ponlas fuera de la tabla en color AMARILLO.
    5. NO uses la palabra "IA". Habla como un experto en salud.
    6. LENGUAJE: {lang}.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/aclarar-duda")
async def aclarar_duda(pregunta: str = Form(...)):
    # Protocolo de Resolución de Dudas para Clientes de Pago
    prompt = f"""
    EL CLIENTE TIENE UNA DUDA SOBRE EL REPORTE: "{pregunta}"
    Responde como el Asesor Senior de AURA. 
    - Sé directo.
    - Explica por qué hay variaciones de precio entre estados.
    - No des órdenes médicas, da sugerencias de ahorro.
    - Tono: Altamente profesional y empático.
    """
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"respuesta": response.choices[0].message.content}

@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    if plan == "donacion": return {"url": PRICE_IDS["donacion"]}
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": PRICE_IDS[plan], "quantity": 1}],
        mode="payment",
        success_url="https://aura-by.onrender.com/?success=true",
        cancel_url="https://aura-by.onrender.com/"
    )
    return {"url": session.url}

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f: return f.read()
