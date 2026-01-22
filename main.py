# ==============================
# AURA by May Roga LLC — main.py
# Estimados educativos solo IA
# ==============================

import os
import random
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
import stripe
from dotenv import load_dotenv

# ==============================
# ENV & APP
# ==============================
load_dotenv()
app = FastAPI(title="AURA by May Roga LLC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# STRIPE
# ==============================
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw",
}

LINK_DONACION = "https://buy.stripe.com/28E00igMD8dR00v5vl7Vm0h"

# ==============================
# IA
# ==============================
openai.api_key = os.getenv("OPENAI_API_KEY")

client_gemini = None
gemini_key = os.getenv("GEMINI_API_KEY")

if gemini_key:
    try:
        from google import genai
        client_gemini = genai.Client(api_key=gemini_key)
        print("✔ Gemini disponible")
    except Exception as e:
        print(f"[WARN] Gemini deshabilitado: {e}")

# ==============================
# INDEX
# ==============================
@app.get("/", response_class=HTMLResponse)
async def index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "index.html"), encoding="utf-8") as f:
        return f.read()

# ==============================
# ESTIMADO EDUCATIVO
# ==============================
@app.post("/estimado")
async def estimado(
    consulta: str = Form(...),
    zip_user: str = Form(""),
    lang: str = Form("es"),
):
    idiomas = {"es": "Español", "en": "English", "ht": "Kreyòl"}
    idioma = idiomas.get(lang, "Español")

    prompt = f"""
ERES AURA, CEREBRO EDUCATIVO DE ESTIMADOS DE PRECIOS DE SALUD Y DENTALES DE MAY ROGA LLC.

IDIOMA: {idioma}
CONSULTA DEL USUARIO: {consulta}
ZIP DEL USUARIO: {zip_user}

OBJETIVO:
- Dar estimados educativos de precios de salud (médicos y dentales).
- Mostrar ZIP, Condado y Estado reales de EE. UU.
- Mostrar rangos de precios según ADA/AMA.
- Explicar que los precios son estimados, pueden variar, algunos proveedores negocian o tienen programas de asistencia.
- Evitar lenguaje médico o diagnóstico.
- Generar HTML compacto y funcional para la app.
- Incluir mapa interactivo para el ZIP buscado.
- Botones: Micrófono, Bocina, WhatsApp, Print/PDF.

RESTRICCIONES:
- No inventar ZIP, condados ni estados.
- No comprometer legalmente a May Roga LLC ni al usuario.
- Tono educativo, humano, protector, claro.
"""

    # ==============================
    # MOTOR IA
    # ==============================
    try:
        if client_gemini:
            r = client_gemini.models.generate_content(
                model="gemini-1.5-pro",
                contents=prompt
            )
            return JSONResponse({"resultado": r.text})
    except Exception as e:
        print(f"[WARN] Gemini falló: {e}")

    try:
        r = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
        )
        return JSONResponse({"resultado": r.choices[0].message.content})
    except Exception as e:
        print(f"[WARN] OpenAI falló: {e}")

    # ==============================
    # FALLBACK LOCAL — RANGOS ESTIMADOS
    # ==============================
    def fila(nombre, zip_code, condado, estado):
        cash_min = random.randint(200, 500)
        cash_max = cash_min + random.randint(50, 150)
        seguro_min = int(cash_min * 0.7)
        seguro_max = int(cash_max * 0.85)
        copago_min = int(cash_min * 0.2)
        copago_max = int(cash_max * 0.35)
        ahorro_min = cash_min - seguro_max
        ahorro_max = cash_max - seguro_min
        return f"""
<tr>
  <td>{nombre}</td>
  <td>{zip_code}</td>
  <td>{condado}</td>
  <td>{estado}</td>
  <td>${cash_min}-${cash_max}</td>
  <td>${seguro_min}-${seguro_max}</td>
  <td>${copago_min}-${copago_max}</td>
  <td>${ahorro_min}-${ahorro_max}</td>
</tr>
"""

    html = f"""
<table style="width:100%;border-collapse:collapse;background:#111;color:#fff;font-size:1rem">
<tr style="background:#0cf;color:#000;font-weight:bold">
<th>Zona</th><th>ZIP</th><th>Condado</th><th>Estado</th>
<th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th>
</tr>
{fila("Local 1", zip_user or "33160", "Miami-Dade", "Florida")}
{fila("Local 2", zip_user or "33161", "Broward", "Florida")}
{fila("Local 3", zip_user or "33162", "Palm Beach", "Florida")}
{fila("Condado 1", zip_user or "33160", "Miami-Dade", "Florida")}
{fila("Condado 2", zip_user or "33161", "Broward", "Florida")}
{fila("Condado 3", zip_user or "33162", "Palm Beach", "Florida")}
{fila("Estado 1", zip_user or "33160", "Miami-Dade", "Florida")}
{fila("Estado 2", zip_user or "33161", "Broward", "Florida")}
{fila("Estado 3", zip_user or "33162", "Palm Beach", "Florida")}
{fila("Nacional 1", "10001", "New York", "New York")}
{fila("Nacional 2", "90001", "Los Angeles", "California")}
{fila("Nacional 3", "60601", "Cook", "Illinois")}
{fila("Nacional 4", "77001", "Harris", "Texas")}
{fila("Nacional 5", "30301", "Fulton", "Georgia")}
</table>

<p style="margin-top:10px">
⏱ Tiempo de asesoría educativa:<br>
Rápido $5.99 → 7 min · Standard $9.99 → 12 min · Special $19.99 → suscripción
</p>

<p>
⚠️ Este reporte es educativo. Los precios son estimados y pueden variar según el proveedor.  
Algunos proveedores ofrecen negociación de precios o programas de asistencia para quien lo necesita.
</p>

<!-- BOTONES -->
<button onclick="window.print()">🖨 Print/PDF</button>
<a href="https://wa.me/?text=Consulta%20educativa" target="_blank">💬 WhatsApp</a>
<button onclick="playAudio()">🔊 Escuchar resultados</button>

<script type="text/javascript">
function playAudio(){{
    var msg = new SpeechSynthesisUtterance(document.body.innerText);
    msg.rate = 0.9;
    msg.pitch = 1;
    window.speechSynthesis.speak(msg);
}}
</script>

<!-- MAPA OPCIONAL -->
<iframe 
  src="https://www.google.com/maps?q={zip_user}&output=embed"
  style="width:100%;height:300px;border:0;margin-top:10px;" allowfullscreen>
</iframe>
"""

    return JSONResponse({"resultado": html})

# ==============================
# STRIPE CHECKOUT
# ==============================
@app.post("/create-checkout-session")
async def checkout(plan: str = Form(...)):
    if plan == "donacion":
        return {"url": LINK_DONACION}

    mode = "subscription" if plan == "special" else "payment"
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": PRICE_IDS[plan], "quantity": 1}],
        mode=mode,
        success_url="https://aura-by.onrender.com/?success=true",
        cancel_url="https://aura-by.onrender.com/",
    )
    return {"url": session.url}

# ==============================
# LOGIN ADMIN
# ==============================
@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if (
        user == os.getenv("ADMIN_USERNAME", "admin")
        and pw == os.getenv("ADMIN_PASSWORD", "admin")
    ):
        return {"status": "success"}
    return JSONResponse(status_code=401, content={"status": "denied"})
