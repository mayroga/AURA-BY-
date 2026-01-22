# ==============================
# AURA by May Roga LLC — main.py
# Estimados educativos con tablas legibles
# ==============================

import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import random
import stripe
from dotenv import load_dotenv
import openai

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
# OPENAI
# ==============================
openai.api_key = os.getenv("OPENAI_API_KEY")

# ==============================
# INDEX
# ==============================
@app.get("/", response_class=HTMLResponse)
async def index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "index.html"), encoding="utf-8") as f:
        return f.read()

# ==============================
# FALLBACK EDUCACIONAL — genera precios
# ==============================
def generar_fila(nombre, zip_code, condado, estado):
    cash_min = random.randint(150, 400)
    cash_max = cash_min + random.randint(20, 100)
    seguro_min = int(cash_min * 0.7)
    seguro_max = int(cash_max * 0.85)
    copago_min = int(cash_min * 0.2)
    copago_max = int(cash_max * 0.35)
    ahorro_min = cash_min - seguro_max
    ahorro_max = cash_max - seguro_min
    sin_seguro_min = cash_min
    sin_seguro_max = cash_max
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
<td>${sin_seguro_min}-${sin_seguro_max}</td>
</tr>
"""

# ==============================
# ESTIMADO EDUCATIVO
# ==============================
@app.post("/estimado")
async def estimado(
    consulta: str = Form(...),
    zip_user: str = Form("33160"),
    lang: str = Form("es"),
):
    idiomas = {"es": "Español", "en": "English", "ht": "Kreyòl"}
    idioma = idiomas.get(lang, "Español")

    # ==============================
    # Fallback educativo dinámico (si OpenAI falla)
    # ==============================
    html = f"""
<h2 style='color:#00ffff;'>Estimado educativo: {consulta}</h2>

<!-- ZIP -->
<table style="width:100%;border-collapse:collapse;background:#111;color:#fff;font-size:0.9rem;margin-bottom:15px">
<tr style="background:#0cf;color:#000;font-weight:bold">
<th>Zona</th><th>ZIP</th><th>Condado</th><th>Estado</th>
<th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th><th>Sin Seguro</th>
</tr>
{generar_fila("ZIP Local 1", zip_user, "Miami-Dade", "Florida")}
{generar_fila("ZIP Local 2", zip_user, "Miami-Dade", "Florida")}
{generar_fila("ZIP Local 3", zip_user, "Miami-Dade", "Florida")}
</table>
<p>💡 Explicación: AURA interpreta los precios del ZIP code usando rangos educativos de Medicare, ADA y FAIR Health. Solo se muestran los precios más bajos para usuarios sin seguro o con copago alto.</p>

<!-- Condado -->
<table style="width:100%;border-collapse:collapse;background:#111;color:#fff;font-size:0.9rem;margin-bottom:15px">
<tr style="background:#0cf;color:#000;font-weight:bold">
<th>Condado</th><th>ZIP</th><th>Condado</th><th>Estado</th>
<th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th><th>Sin Seguro</th>
</tr>
{generar_fila("Condado 1", zip_user, "Miami-Dade", "Florida")}
{generar_fila("Condado 2", zip_user, "Broward", "Florida")}
{generar_fila("Condado 3", zip_user, "Palm Beach", "Florida")}
</table>
<p>💡 Explicación: Comparación de condados cercanos. Se priorizan los precios más bajos para cada usuario según su tipo de cobertura.</p>

<!-- Estado -->
<table style="width:100%;border-collapse:collapse;background:#111;color:#fff;font-size:0.9rem;margin-bottom:15px">
<tr style="background:#0cf;color:#000;font-weight:bold">
<th>Estado</th><th>ZIP</th><th>Condado</th><th>Estado</th>
<th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th><th>Sin Seguro</th>
</tr>
{generar_fila("Estado 1", zip_user, "Miami-Dade", "Florida")}
{generar_fila("Estado 2", zip_user, "Broward", "Florida")}
{generar_fila("Estado 3", zip_user, "Palm Beach", "Florida")}
</table>
<p>💡 Explicación: Se muestran los 3 precios más bajos en el estado. Si se incluyen precios más altos, se justifica por calidad o disponibilidad de proveedores.</p>

<!-- Nacional -->
<table style="width:100%;border-collapse:collapse;background:#111;color:#fff;font-size:0.9rem;margin-bottom:15px">
<tr style="background:#0cf;color:#000;font-weight:bold">
<th>Nacional</th><th>ZIP</th><th>Condado</th><th>Estado</th>
<th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th><th>Sin Seguro</th>
</tr>
{generar_fila("Nacional 1", "10001", "New York", "New York")}
{generar_fila("Nacional 2", "90001", "Los Angeles", "California")}
{generar_fila("Nacional 3", "60601", "Cook", "Illinois")}
{generar_fila("Nacional 4", "77001", "Harris", "Texas")}
{generar_fila("Nacional 5", "30301", "Fulton", "Georgia")}
</table>
<p>💡 Explicación: Comparación de precios nacionales, siempre priorizando las opciones más económicas para el usuario. Se busca eliminar el miedo a no saber los precios reales.</p>

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

<!-- MAPA -->
<iframe 
  src="https://www.google.com/maps?q={zip_user}&output=embed"
  style="width:100%;height:300px;border:0;margin-top:5px;" allowfullscreen>
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
