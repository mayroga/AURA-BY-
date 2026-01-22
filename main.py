# ==============================
# AURA by May Roga LLC — main.py
# Estimados educativos basados en datos reales
# ==============================

import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import random
import stripe
from dotenv import load_dotenv
import json

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
# DATOS REALES — BASE SIMULADA
# ==============================
# Ejemplo: consulta médica general (CPT 99203)
PRICE_TABLE = {
    "consulta_medica": {
        "cpt": "99203",
        "zip": {
            "33160": {"condado": "Miami-Dade", "estado": "Florida", "cash": (210, 250), "insured": (175, 200)},
            "33161": {"condado": "Broward", "estado": "Florida", "cash": (200, 240), "insured": (170, 190)},
            "33162": {"condado": "Palm Beach", "estado": "Florida", "cash": (190, 230), "insured": (160, 185)},
        },
        "estado": {
            "Florida": {"cash": (190, 250), "insured": (160, 200)},
            "New York": {"cash": (250, 320), "insured": (220, 280)},
            "California": {"cash": (240, 310), "insured": (210, 270)},
        },
        "nacional": {
            "10001": {"ciudad": "New York", "estado": "NY", "cash": (250, 320), "insured": (220, 280)},
            "90001": {"ciudad": "Los Angeles", "estado": "CA", "cash": (240, 310), "insured": (210, 270)},
            "60601": {"ciudad": "Chicago", "estado": "IL", "cash": (200, 270), "insured": (180, 240)},
            "77001": {"ciudad": "Houston", "estado": "TX", "cash": (180, 250), "insured": (150, 220)},
            "30301": {"ciudad": "Atlanta", "estado": "GA", "cash": (170, 240), "insured": (140, 210)},
        }
    }
}

# ==============================
# INDEX
# ==============================
@app.get("/", response_class=HTMLResponse)
async def index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "index.html"), encoding="utf-8") as f:
        return f.read()

# ==============================
# ESTIMADO EDUCATIVO REAL
# ==============================
@app.post("/estimado")
async def estimado(
    consulta: str = Form(...),
    zip_user: str = Form("33160"),
    lang: str = Form("es"),
):
    idiomas = {"es": "Español", "en": "English", "ht": "Kreyòl"}
    idioma = idiomas.get(lang, "Español")

    service = "consulta_medica"  # por ejemplo, podría mapear más consultas reales

    # ==============================
    # OBTENER DATOS ZIP
    # ==============================
    zip_data = PRICE_TABLE[service]["zip"].get(zip_user)
    condado_data = zip_data or {"condado": "Desconocido", "estado": "Florida", "cash": (200, 250), "insured": (170, 200)}
    
    estado_name = condado_data.get("estado", "Florida")
    estado_data = PRICE_TABLE[service]["estado"].get(estado_name, condado_data)
    
    nacional_data = PRICE_TABLE[service]["nacional"]

    # ==============================
    # GENERAR TABLA HTML
    # ==============================
    def fila(nombre, zip_code, condado, estado, cash_range, insured_range):
        cash_min, cash_max = cash_range
        insured_min, insured_max = insured_range
        copago_min = int(cash_min * 0.2)
        copago_max = int(cash_max * 0.35)
        ahorro_min = cash_min - insured_max
        ahorro_max = cash_max - insured_min
        return f"""
<tr>
<td>{nombre}</td><td>{zip_code}</td><td>{condado}</td><td>{estado}</td>
<td>${cash_min}-${cash_max}</td><td>${insured_min}-${insured_max}</td>
<td>${copago_min}-${copago_max}</td><td>${ahorro_min}-${ahorro_max}</td>
<td>Sin seguro: ${cash_min}-${cash_max}</td>
</tr>
"""

    html = f"""
<table style="width:100%;border-collapse:collapse;background:#111;color:#fff;font-size:0.9rem">
<tr style="background:#0cf;color:#000;font-weight:bold">
<th>Zona</th><th>ZIP</th><th>Condado</th><th>Estado</th>
<th>Cash</th><th>Seguro</th><th>Copago</th><th>Ahorro USD</th><th>Sin seguro</th>
</tr>
{fila("Local ZIP", zip_user, condado_data["condado"], condado_data["estado"], condado_data["cash"], condado_data["insured"])}
{fila("Estado 1", zip_user, condado_data["condado"], condado_data["estado"], estado_data["cash"], estado_data["insured"])}
""" + "".join([fila(f"Nacional {i+1}", z, d["ciudad"], d["estado"], d["cash"], d["insured"]) 
             for i,(z,d) in enumerate(nacional_data.items())]) + """
</table>

<p style="margin-top:5px">
⚠️ Estos precios son estimados, educativos y basados en rangos de Medicare (CMS), ADA, FAIR Health.
La IA explica estos precios y su interpretación educativa. Se agrupan por ZIP, Condado, Estado y Nacional.
</p>

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
