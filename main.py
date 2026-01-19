import os
import sqlite3
import stripe
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw",
    "donacion": "price_1SnatfBOA5mT4t0PZouWzfpw" # O tu ID de donación real
}

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def query_sql_3351(termino, zip_user=None):
    try:
        conn = sqlite3.connect('cost_estimates.db')
        cur = conn.cursor()
        b = f"%{termino.upper()}%"
        cur.execute("SELECT * FROM cost_estimates WHERE description LIKE ? AND zip_code = ? LIMIT 3", (b, zip_user))
        locales = cur.fetchall()
        cur.execute("SELECT * FROM cost_estimates WHERE description LIKE ? ORDER BY low_price ASC LIMIT 5", (b,))
        nacionales = cur.fetchall()
        cur.execute("SELECT * FROM cost_estimates WHERE description LIKE ? ORDER BY high_price DESC LIMIT 1", (b,))
        premium = cur.fetchone()
        conn.close()
        return {"locales": locales, "nacionales": nacionales, "premium": premium}
    except: return None

@app.get("/", response_class=HTMLResponse)
async def read_index():
    # Render necesita el path absoluto o estar en la misma carpeta
    path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):
    datos = query_sql_3351(consulta, zip_user)
    # PROMPT REFORZADO PARA IDIOMA
    prompt = f"""
    YOU ARE AURA, EXPERT FROM MAY ROGA LLC. 
    RESPONSE LANGUAGE: Use ONLY {lang}. (es=Spanish, en=English, ht=Haitian Creole).
    
    PROCEDURE: {consulta} | ZIP: {zip_user}
    DATA: {datos}
    
    ESTRUCTURA 3-3-5-1 (OBLIGATORIA EN TABLAS HTML):
    1. Header con nombre de procedimiento.
    2. 3 LOCALES (Cerca de {zip_user}).
    3. 5 NACIONALES (Más económicas de USA).
    4. 1 PREMIUM (Más costosa).
    
    REGLAS: No digas 'IA', 'Gobierno'. Sé profesional y directo.
    """
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/aclarar-duda")
async def aclarar_duda(pregunta: str = Form(...), contexto: str = Form(...), lang: str = Form("es")):
    prompt = f"Responde esta duda del cliente en idioma {lang}: {pregunta}. Contexto: {contexto}. Sé breve."
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    # Credenciales solicitadas
    if user == "USERB=NAME" and pw == "CLAVE":
        return {"status": "ok"}
    return JSONResponse(status_code=401, content={"error": "Invalid"})

@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    price_id = PRICE_IDS.get(plan)
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{'price': price_id, 'quantity': 1}],
        mode='payment',
        success_url="https://aura-by.onrender.com/?success=true",
        cancel_url="https://aura-by.onrender.com/?cancel=true",
    )
    return {"id": session.id}
