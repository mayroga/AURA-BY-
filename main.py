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

# IDs DE STRIPE ACTUALIZADOS SEGÚN SOLICITUD
PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw"
}

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def query_aura_brain(termino, zip_user):
    try:
        conn = sqlite3.connect('aura_brain.db')
        cur = conn.cursor()
        search = f"%{termino.upper()}%"
        
        # 3 Locales
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE description LIKE ? AND zip_code = ? LIMIT 3", (search, zip_user))
        locales = cur.fetchall()
        
        # 3 Condado/Estado (usando los primeros 3 dígitos del ZIP)
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE description LIKE ? AND zip_code LIKE ? LIMIT 3", (search, f"{zip_user[:3]}%"))
        condado = cur.fetchall()

        # 5 Nacionales (Los más baratos de todo USA)
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE (description LIKE ? OR cpt_code LIKE ?) ORDER BY low_price ASC LIMIT 5", (search, search))
        nacionales = cur.fetchall()
        
        conn.close()
        return {"locales": locales, "condado": condado, "nacionales": nacionales}
    except: return None

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form("33101")):
    datos_sql = query_aura_brain(consulta, zip_user)
    
    prompt = f"""
    ERES AURA BY MAY ROGA LLC. ASESOR PROFESIONAL DE PRECIOS MÉDICOS (MEDICARE/CMS EXPERT).
    OBJETIVO: Eliminar el miedo al precio oculto mediante transparencia.
    
    REGLAS DE RESPUESTA:
    1. FORMATO: Usa exclusivamente TABLAS HTML claras. No párrafos largos.
    2. TABLAS REQUERIDAS:
       - TABLA 1: 3 Precios más bajos detectados en Zip Code {zip_user}.
       - TABLA 2: 3 Opciones económicas en el Condado/Estado.
       - TABLA 3: 5 OPCIONES DE AHORRO NACIONAL (Indica Ciudad, Estado y Zip Code exacto).
       - TABLA 4: 1 Opción Premium (Referencia de mercado alto).
    3. COLUMNAS: [Ubicación (Zip/Estado)] | [Servicio/Código] | [Precio CASH Estimado] | [Ahorro vs Promedio].
    4. PROTOCOLO DE ASESORÍA: Si el usuario tiene dudas, aclara que este es un estimado educativo basado en CPT 2026 (AMA) y CDT (ADA).
    5. No ataques a las aseguradoras, simplemente compara los datos.
    6. DATOS SQL ACTUALES: {datos_sql}
    7. Si no hay datos en SQL, utiliza tu conocimiento experto de los 'Physician Fee Schedules' de 2026 para rellenar las tablas con datos realistas de mercado.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/ask-aura")
async def ask_aura(pregunta: str = Form(...)):
    # PROTOCOLO DE ACLARACIÓN DE DUDAS PARA CLIENTES PAGOS
    prompt = f"El cliente ha pagado por asesoría profesional. Responde de forma técnica pero comprensible sobre esta duda médica/financiera: {pregunta}. Mantén el tono de asesor, no de gobierno."
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": PRICE_IDS[plan], "quantity": 1}],
        mode="payment",
        success_url="https://aura-by.onrender.com/?success=true",
        cancel_url="https://aura-by.onrender.com/"
    )
    return {"url": session.url}

@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    # Credenciales desde variables de entorno de Render
    if user == os.getenv("ADMIN_USERNAME") and pw == os.getenv("ADMIN_PASSWORD"):
        return {"status": "ok"}
    return JSONResponse(status_code=401)

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f: return f.read()
