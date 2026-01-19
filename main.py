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

# Configuración Stripe & OpenAI
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

# IDs de Precios Reales
PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw"
}
LINK_DONACION = "https://buy.stripe.com/28E00igMD8dR00v5vl7Vm0h"

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- Función de consulta SQL con precios de usuarios ---
def query_sql_3351(termino, zip_user=None):
    try:
        conn = sqlite3.connect('cost_estimates.db')
        cur = conn.cursor()
        b = f"%{termino.upper()}%"
        
        # Precios oficiales
        cur.execute("SELECT * FROM cost_estimates WHERE description LIKE ? AND zip_code = ? LIMIT 3", (b, zip_user))
        locales = cur.fetchall()
        cur.execute("SELECT * FROM cost_estimates WHERE description LIKE ? AND state = ? LIMIT 3", (b, zip_user[:2] if zip_user else ""))
        regionales = cur.fetchall()
        cur.execute("SELECT * FROM cost_estimates WHERE description LIKE ? ORDER BY low_price ASC LIMIT 5", (b,))
        nacionales = cur.fetchall()
        cur.execute("SELECT * FROM cost_estimates WHERE description LIKE ? ORDER BY high_price DESC LIMIT 1", (b,))
        premium = cur.fetchone()

        # Precios reportados por usuarios
        cur.execute("SELECT * FROM user_prices WHERE code LIKE ? AND zip_code = ?", (f"%{termino.upper()}%", zip_user))
        user_reports = cur.fetchall()
        
        conn.close()
        return {
            "locales": locales, 
            "regionales": regionales, 
            "nacionales": nacionales, 
            "premium": premium,
            "user_reports": user_reports
        }
    except:
        return None

# --- Página principal ---
@app.get("/", response_class=HTMLResponse)
async def read_index():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "Error: index.html no encontrado."

# --- Estimado con traducción ---
@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):
    datos = query_sql_3351(consulta, zip_user)
    
    prompt = f"""
    ERES AURA, EL CEREBRO ASESOR DE MAY ROGA LLC.
    TU RESPUESTA DEBE SER EN {lang.upper()}.
    REGLA 3-3-5-1: 3 precios locales, 3 estatales, 5 nacionales, 1 premium.
    DATOS SQL: {datos}
    INSTRUCCIONES ADICIONALES:
    - Incluye precios reportados por usuarios como 'No verificado'.
    - Nunca los combines con precios oficiales, solo comparativos.
    - Resalta si son más bajos o más altos que los oficiales.
    FORMATO: Tablas HTML, columnas Nivel/Ubicación/Precio Cash/Precio Seguro.
    """
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return {"resultado": response.choices[0].message.content}

# --- Stripe Checkout ---
@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    if plan == "donacion":
        return {"url": LINK_DONACION}
    
    price_id = PRICE_IDS.get(plan)
    if not price_id:
        return JSONResponse(status_code=400, content={"error": "Plan inválido"})
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='payment',
            success_url="https://aura-by.onrender.com/?success=true",
            cancel_url="https://aura-by.onrender.com/",
        )
        return {"url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- Login Admin ---
@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if user == os.getenv("ADMIN_USERNAME") and pw == os.getenv("ADMIN_PASSWORD"):
        return {"status": "ok"}
    return JSONResponse(status_code=401, content={"error": "Invalid"})

# --- Aclarar duda ---
@app.post("/aclarar-duda")
async def aclarar_duda(pregunta: str = Form(...), contexto: str = Form(...)):
    prompt = f"Responde como Aura de May Roga LLC a la duda sobre este reporte: {contexto}. Pregunta: {pregunta}. Sé breve y profesional."
    response = openai.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return {"resultado": response.choices[0].message.content}

# --- Reporte de precios por usuarios ---
@app.post("/reportar-precio")
async def reportar_precio(code: str = Form(...), zip_user: str = Form(...), state: str = Form(...), precio: float = Form(...), nota: str = Form("Reporte usuario")):
    try:
        conn = sqlite3.connect('cost_estimates.db')
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_prices (code, zip_code, state, reported_price, note)
            VALUES (?,?,?,?,?)
        """, (code.upper(), zip_user, state.upper(), precio, nota))
        conn.commit()
        conn.close()
        return {"status": "ok", "msg": "Precio reportado guardado"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
