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

def query_aura_brain(termino, zip_user):
    try:
        conn = sqlite3.connect('aura_brain.db')
        cur = conn.cursor()
        b = f"%{termino.upper()}%"
        
        # 3 LOCALES (ZIP)
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE description LIKE ? AND zip_code = ? LIMIT 3", (b, zip_user))
        locales = cur.fetchall()
        
        # 3 CONDADO (ZIP Prefix)
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE description LIKE ? AND zip_code LIKE ? LIMIT 3", (b, f"{zip_user[:3]}%"))
        condado = cur.fetchall()
        
        # 5 NACIONALES (MÁS BAJOS DE USA)
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE description LIKE ? ORDER BY low_price ASC LIMIT 5", (b,))
        nacionales = cur.fetchall()

        # 1 PREMIUM
        cur.execute("SELECT description, high_price, state, zip_code FROM prices WHERE description LIKE ? ORDER BY high_price DESC LIMIT 1", (b,))
        premium = cur.fetchone()
        
        conn.close()
        return {"zip": locales, "condado": condado, "nacionales": nacionales, "premium": premium}
    except: return None

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form("")):
    datos = query_aura_brain(consulta, zip_user)
    
    prompt = f"""
    ERES AURA, EL CEREBRO DE MAY ROGA LLC. EXPERTO PROFESIONAL.
    IDIOMA DE RESPUESTA: {lang}.
    
    ESTRUCTURA OBLIGATORIA (Usa tablas HTML):
    1. 3 PRECIOS MÁS BAJOS EN ZIP {zip_user}.
    2. 3 PRECIOS EN EL CONDADO.
    3. 5 PRECIOS MÁS BAJOS EN TODO USA (Enfócate en el ahorro).
    4. 1 OPCIÓN PREMIUM (Referencia de alto costo).
    
    DATOS REALES: {datos}
    
    REGLAS:
    - No uses "IA" ni "Gobierno". 
    - Sé profesional e interesante.
    - Si no hay datos, da un rango estimado basado en mercado real de USA.
    - Explica por qué conviene viajar a otro estado si el ahorro es grande.
    - Termina con BLINDAJE LEGAL de May Roga LLC.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/aclarar-duda")
async def aclarar_duda(pregunta: str = Form(...), contexto: str = Form(...)):
    prompt = f"Como Aura de May Roga LLC, responde de forma breve y experta a esta duda del cliente sobre su reporte: {pregunta}. Contexto: {contexto}"
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

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
