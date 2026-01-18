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

# Credenciales Admin de RENDER
ADMIN_USER = os.getenv("ADMIN_USERNAME")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def query_3351(termino, zip_user=None):
    try:
        conn = sqlite3.connect('cost_estimates.db') # Asegúrate que este sea el nombre de tu DB
        cur = conn.cursor()
        busqueda = f"%{termino.strip().upper()}%"
        
        # 3 LOCALES (ZIP exacto)
        locales = []
        if zip_user:
            cur.execute("SELECT description, state, zip_code, low_price FROM cost_estimates WHERE (description LIKE ? OR cpt_code LIKE ?) AND zip_code = ? ORDER BY low_price ASC LIMIT 3", (busqueda, busqueda, zip_user))
            locales = cur.fetchall()

        # 3 REGIONALES (Mismo Estado, diferente ZIP)
        regionales = []
        if zip_user:
            state_prefix = zip_user[:2]
            cur.execute("SELECT description, state, zip_code, low_price FROM cost_estimates WHERE (description LIKE ? OR cpt_code LIKE ?) AND state LIKE ? AND zip_code != ? ORDER BY low_price ASC LIMIT 3", (busqueda, busqueda, f"{state_prefix}%", zip_user))
            regionales = cur.fetchall()

        # 5 NACIONALES (Más baratos de todo el país)
        cur.execute("SELECT description, state, zip_code, low_price FROM cost_estimates WHERE (description LIKE ? OR cpt_code LIKE ?) ORDER BY low_price ASC LIMIT 5", (busqueda, busqueda))
        nacionales = cur.fetchall()

        # 1 PREMIUM (El más alto registrado)
        cur.execute("SELECT description, state, zip_code, high_price FROM cost_estimates WHERE (description LIKE ? OR cpt_code LIKE ?) ORDER BY high_price DESC LIMIT 1", (busqueda, busqueda))
        premium = cur.fetchone()

        conn.close()
        return {"locales": locales, "regionales": regionales, "nacionales": nacionales, "premium": premium}
    except:
        return None

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if user == ADMIN_USER and pw == ADMIN_PASS:
        return {"status": "success"}
    return JSONResponse(status_code=401, content={"status": "error"})

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):
    datos = query_3351(consulta, zip_user)
    
    prompt = f"""
    Eres AURA de May Roga LLC. Asesor experto en costos médicos.
    USUARIO BUSCA: {consulta}
    ZIP: {zip_user}
    DATOS SQL (Estructura 3-3-5-1): {datos}

    INSTRUCCIONES:
    1. Presenta 3 opciones LOCALES económicas.
    2. Presenta 3 opciones REGIONALES (Estado/Condado).
    3. Presenta 5 opciones NACIONALES (las más baratas de USA).
    4. Presenta 1 opción PREMIUM de alto costo.
    5. Usa un lenguaje profesional. NO digas 'IA', 'Gobierno' o 'Auditoría'.
    6. Resalta en negrita el nombre del procedimiento solicitado.
    7. Al final incluye el BLINDAJE LEGAL de May Roga LLC.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/aclarar-duda")
async def aclarar_duda(pregunta: str = Form(...), contexto: str = Form(...), lang: str = Form("es")):
    prompt = f"El cliente tiene una duda sobre su reporte de costos. Responde de forma profesional. Contexto: {contexto}. Pregunta: {pregunta}."
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    prices = {"rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq", "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE", "special": "price_1SnatfBOA5mT4t0PZouWzfpw"}
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": prices[plan.lower()], "quantity": 1}],
        mode="payment",
        success_url="https://aura-by.onrender.com/?success=true",
        cancel_url="https://aura-by.onrender.com/"
    )
    return {"url": session.url}
