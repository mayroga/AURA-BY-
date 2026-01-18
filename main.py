import os
import sqlite3
import stripe
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from google import genai
import openai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# ==============================
# Configuración Stripe & IA
# ==============================
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
client_gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")

# Precios de acceso
PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw"
}
LINK_DONACION = "https://buy.stripe.com/28E00igMD8dR00v5vl7Vm0h"

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ==============================
# Función SQL avanzada
# ==============================
def query_sql(termino, zip_user=None):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'cost_estimates.db')
        if not os.path.exists(db_path):
            return "SQL_OFFLINE"

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        busqueda = f"%{termino.strip().upper()}%"

        # Buscar local -> condado -> estado -> nacional
        cursor.execute("""
        SELECT cpt_code, description, state, zip_code, low_price, high_price
        FROM cost_estimates
        WHERE description LIKE ? OR cpt_code LIKE ?
        ORDER BY low_price ASC
        LIMIT 20
        """, (busqueda, busqueda))
        results = cursor.fetchall()
        conn.close()

        if not results:
            return "DATO_NO_SQL"

        # Separar resultados locales, condado, estado, nacional
        local, county, state, national = [], [], [], []
        for r in results:
            code, desc, state_r, zip_r, low, high = r
            # Local
            if zip_user and zip_r == zip_user:
                local.append(r)
            # Condado (primer 3 dígitos ZIP)
            elif zip_user and zip_r.startswith(zip_user[:3]):
                county.append(r)
            # Estado
            elif zip_user and state_r == zip_user[:2]:
                state.append(r)
            else:
                national.append(r)

        return {
            "local": local[:3],
            "county": county[:3],
            "state": state[:3],
            "national": national[:5]  # Top 5 más baratos nacionales
        }

    except Exception as e:
        print(f"[ERROR SQL] {e}")
        return f"ERROR_SQL: {str(e)}"

# ==============================
# Ruta principal
# ==============================
@app.get("/", response_class=HTMLResponse)
async def read_index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

# ==============================
# Obtener estimado con IA + SQL
# ==============================
@app.post("/estimado")
async def obtener_estimado(
    consulta: str = Form(...),
    lang: str = Form("es"),
    zip_user: str = Form(None)
):
    datos_sql = query_sql(consulta, zip_user)

    idiomas = {"es": "Español", "en": "English", "ht": "Kreyòl (Haitian Creole)"}
    idioma_destino = idiomas.get(lang, "Español")

    prompt = f"""
ERES AURA, MOTOR DE ESTIMADOS DE PRECIOS MÉDICOS Y DENTALES DE MAY ROGA LLC.
IDIOMA: {idioma_destino}
DATOS SQL ENCONTRADOS: {datos_sql}
CONSULTA DEL USUARIO: {consulta}
ZIP DETECTADO: {zip_user}

OBJETIVO:
1) Mostrar al usuario sin seguro los precios más baratos locales, del condado, del estado y nacionales.
2) Comparar con precio de seguros si existe.
3) Mostrar opción premium para clientes con alto poder adquisitivo.
4) Explicación clara y sencilla, resaltando en azul lo que el usuario preguntó.
5) Incluye top 3 locales, top 3 condado, top 3 estado, top 5 nacionales.
6) Siempre dar contexto de ahorro y ventajas/desventajas de cada opción.
7) Resumen final como "libro abierto" para el usuario.
"""

    motores = []
    # Gemini
    try:
        modelos_gemini = client_gemini.models.list().data
        if modelos_gemini:
            motores.append(("gemini", modelos_gemini[0].name))
    except: pass

    # OpenAI fallback
    try: motores.append(("openai", "gpt-4"))
    except: pass

    for motor, modelo in motores:
        try:
            if motor == "gemini":
                response = client_gemini.models.generate_content(model=modelo, contents=prompt)
                return {"resultado": response.text}
            elif motor == "openai":
                response = openai.chat.completions.create(
                    model=modelo,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                )
                return {"resultado": response.choices[0].message.content}
        except:
            continue

    return {"resultado": "Estimado generado automáticamente sin datos exactos SQL."}

# ==============================
# Crear sesión Stripe
# ==============================
@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    if plan.lower() == "donacion":
        return {"url": LINK_DONACION}
    try:
        mode = "subscription" if plan.lower() == "special" else "payment"
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_IDS[plan.lower()], "quantity": 1}],
            mode=mode,
            success_url="https://aura-iyxa.onrender.com/?success=true",
            cancel_url="https://aura-iyxa.onrender.com/"
        )
        return {"url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==============================
# Login Admin / Acceso gratuito
# ==============================
@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    ADMIN_USER = os.getenv("ADMIN_USERNAME", "TU_USERNAME")
    ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "TU_PASSWORD")
    if user == ADMIN_USER and pw == ADMIN_PASS:
        return {"status": "success", "access": "full"}
    return JSONResponse(status_code=401, content={"status": "error"})
