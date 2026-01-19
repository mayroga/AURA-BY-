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

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def query_sql_3351(termino, zip_user=None):
    # Lógica para extraer datos según la regla 3-3-5-1
    try:
        conn = sqlite3.connect('cost_estimates.db')
        cur = conn.cursor()
        b = f"%{termino.upper()}%"
       
        # LOCALES (ZIP)
        cur.execute("SELECT * FROM cost_estimates WHERE description LIKE ? AND zip_code = ? LIMIT 3", (b, zip_user))
        locales = cur.fetchall()
       
        # CONDADO / ESTADO
        cur.execute("SELECT * FROM cost_estimates WHERE description LIKE ? AND state = ? LIMIT 3", (b, zip_user[:2] if zip_user else ""))
        regionales = cur.fetchall()
       
        # NACIONALES (5 más bajos)
        cur.execute("SELECT * FROM cost_estimates WHERE description LIKE ? ORDER BY low_price ASC LIMIT 5", (b,))
        nacionales = cur.fetchall()
       
        # PREMIUM (1 más alto)
        cur.execute("SELECT * FROM cost_estimates WHERE description LIKE ? ORDER BY high_price DESC LIMIT 1", (b,))
        premium = cur.fetchone()
       
        conn.close()
        return {"locales": locales, "regionales regionales": regionales, "nacionales": nacionales, "premium": premium}
    except: return None

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):
    datos = query_sql_3351(consulta, zip_user)
   
    # PROMPT MAESTRO PARA EVITAR PÁRRAFOS Y MOSTRAR COMPARACIÓN
    prompt = f"""
    ERES AURA, EL CEREBRO DE MAY ROGA LLC.
    TU CLIENTE PAGÓ POR UN REPORTE DETALLADO Y COMPARATIVO.
   
    PROCEDIMIENTO SOLICITADO: {consulta}
    UBICACIÓN: {zip_user}
   
    ESTRUCTURA OBLIGATORIA DEL REPORTE (USA HTML PARA TABLAS O DIVS):
   
    1. **ENCABEZADO**: Nombre del procedimiento en azul resaltado.
    2. **ESTRUCTURA 3-3-5-1**:
       - 3 OPCIONES LOCALES (Cerca de {zip_user}).
       - 3 OPCIONES CONDADO/ESTADO.
       - 5 OPCIONES NACIONALES (Los precios más bajos de USA para ahorrar).
       - 1 OPCIÓN PREMIUM (Servicio de lujo/alto costo).
   
    3. **COMPARATIVA DE PAGO POR CADA NIVEL**:
       - Precio CASH (Pago directo).
       - Precio ESTIMADO CON SEGURO (Tarifa negociada típica).
   
    4. **VENTAJAS DE AHORRO**: Por qué elegir las nacionales económicas.
   
    REGLAS CRÍTICAS:
    - No uses párrafos largos. Usa listas, puntos y tablas.
    - NO DIGAS 'IA', 'Inteligencia Artificial', 'Gobierno'.
    - Sé profesional, interesante y experto.
    - Datos de referencia: {datos}
    - Si no hay datos exactos en SQL, sugiere el rango estimado basado en CMS y mercado real de USA.
    - Idioma: {lang}
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/aclarar-duda")
async def aclarar_duda(pregunta: str = Form(...), contexto: str = Form(...)):
    prompt = f"El cliente tiene una duda sobre este reporte de Aura: {contexto}. Pregunta: {pregunta}. Responde como el experto Aura de May Roga LLC de forma breve y resolutiva."
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if user == os.getenv("ADMIN_USERNAME") and pw == os.getenv("ADMIN_PASSWORD"):
        return {"status": "ok"}
    return JSONResponse(status_code=401, content={"error": "Invalid"})

@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    # Lógica de Stripe...
    pass
