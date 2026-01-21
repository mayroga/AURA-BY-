import os
import stripe
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# ==============================
# Configuración Stripe & IA
# ==============================
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Gemini (fallback a OpenAI)
client_gemini = None
gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    try:
        from google import genai
        client_gemini = genai.Client(api_key=gemini_api_key)
    except Exception as e:
        print(f"[WARNING] Gemini no inicializado: {e}")
else:
    print("[WARNING] GEMINI_API_KEY no encontrada, se usará OpenAI")

# OpenAI
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
# Ruta principal
# ==============================
@app.get("/", response_class=HTMLResponse)
async def read_index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

# ==============================
# Función principal IA: estimado educativo
# ==============================
@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):

    idiomas = {"es": "Español", "en": "English", "ht": "Kreyòl (Haitian Creole)"}
    idioma_destino = idiomas.get(lang, "Español")

    prompt = f"""
ERES AURA, MOTOR DE ESTIMADOS EDUCATIVOS DE PRECIOS MÉDICOS Y DENTALES.
IDIOMA: {idioma_destino}
CONSULTA DEL USUARIO: {consulta}
ZIP DETECTADO: {zip_user}

OBJETIVO:
1) Generar ESTIMADOS EDUCATIVOS usando datos históricos oficiales (ADA, AMA) sin mencionarlos.
2) Comparar precios cash, seguro, copago y ahorro potencial en USD.
3) Mostrar opción local, condado, estado y nacional.
4) Crear tabla HTML oscura legible con rangos y ahorros.
5) Explicación clara y sencilla, resaltando en azul la consulta del usuario.
6) Incluir sección de ASESOR LEGAL que explique contexto educativo y blindaje legal.
7) Concluir con BLINDAJE LEGAL: 
   Este reporte es emitido por Aura by May Roga LLC, agencia de información independiente.
   No somos médicos, clínicas ni aseguradoras.
   No damos diagnósticos ni cotizaciones.
   Este es un ESTIMADO EDUCATIVO.
   El proveedor final define el precio.
"""

    motores = []
    if client_gemini:
        try:
            modelos_gemini = client_gemini.models.list().data
            if modelos_gemini:
                motores.append(("gemini", modelos_gemini[0].name))
        except:
            pass
    motores.append(("openai", "gpt-4"))

    for motor, modelo in motores:
        try:
            if motor == "gemini" and client_gemini:
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

    return {"resultado": "<p>Estimado educativo generado automáticamente. Datos exactos no disponibles.</p>"}

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
            success_url="https://aura-by.onrender.com/?success=true",
            cancel_url="https://aura-by.onrender.com/"
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
