# ==============================
# AURA by May Roga LLC
# main.py — PRODUCCIÓN DEFINITIVA
# ==============================

import os
import sqlite3
import stripe
from datetime import datetime

from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

import openai
from dotenv import load_dotenv

# ==============================
# CARGA ENV
# ==============================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "aura_brain.db")

app = FastAPI(title="AURA by May Roga LLC")

# ==============================
# CORS
# ==============================
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

# Gemini ES OPCIONAL
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
# DB
# ==============================
def get_conn():
    return sqlite3.connect(DB_PATH)

def query_prices(term, zip_user=None):
    """
    Consulta educativa interna (si existe).
    Si no hay datos → devuelve vacío (NO error).
    """
    try:
        conn = get_conn()
        cur = conn.cursor()

        like = f"%{term}%"
        cur.execute("""
            SELECT description, cpt_code, low_price, high_price, state, zip_code, county
            FROM prices
            WHERE description LIKE ? OR cpt_code LIKE ?
            ORDER BY low_price ASC
            LIMIT 20
        """, (like, like))

        rows = cur.fetchall()
        conn.close()

        return rows if rows else []

    except Exception:
        return []

# ==============================
# INDEX
# ==============================
@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()

# ==============================
# FORMATEO TABLA OSCURA
# ==============================
def generar_tabla_html(tablas):
    html = """
    <html>
    <head>
    <style>
    body { background-color: #121212; color: #eee; font-family: 'Segoe UI', sans-serif; }
    table { width: 90%; margin: 15px auto; border-collapse: collapse; }
    th, td { border: 1px solid #444; padding: 8px; text-align: center; }
    th { background-color: #1f1f1f; }
    tr:nth-child(even) { background-color: #1a1a1a; }
    tr:nth-child(odd) { background-color: #141414; }
    h2 { text-align: center; color: #00d4ff; }
    </style>
    </head>
    <body>
    """
    for nivel in ['local','county','state','national']:
        if nivel in tablas and tablas[nivel]:
            nivel_nombre = {
                "local":"Local (ZIP)",
                "county":"Condado",
                "state":"Estado",
                "national":"Nacional"
            }[nivel]
            html += f"<h2>{nivel_nombre}</h2>"
            html += "<table><tr><th>Procedimiento</th><th>CPT</th><th>Cash Bajo</th><th>Cash Alto</th>"
            html += "<th>Seguro Bajo</th><th>Seguro Alto</th><th>Copago Bajo</th><th>Copago Alto</th>"
            html += "<th>Ahorro Seguro</th><th>Ahorro Copago</th><th>Estado</th><th>Condado</th><th>ZIP</th></tr>"
            for item in tablas[nivel]:
                html += f"<tr><td>{item['description']}</td><td>{item['code']}</td>"
                html += f"<td>${item['cash_low']}</td><td>${item['cash_high']}</td>"
                html += f"<td>${item['insured_low']}</td><td>${item['insured_high']}</td>"
                html += f"<td>${item['copay_low']}</td><td>${item['copay_high']}</td>"
                html += f"<td>${item['ahorro_seguro']}</td><td>${item['ahorro_copago']}</td>"
                html += f"<td>{item['state']}</td><td>{item['county']}</td><td>{item['zip_code']}</td></tr>"
            html += "</table>"
    html += "</body></html>"
    return html

# ==============================
# ESTIMADO PRINCIPAL (NUNCA FALLA)
# ==============================
@app.post("/estimado", response_class=HTMLResponse)
async def estimado(
    consulta: str = Form(...),
    lang: str = Form("es"),
    zip_user: str = Form(None),
):

    datos_locales = query_prices(consulta, zip_user)

    # ==============================
    # GENERAR TABLAS DE RESULTADOS
    # ==============================
    # Local
    tablas = {"local": [], "county": [], "state": [], "national": []}
    if datos_locales:
        # Local ZIP
        local = sorted([d for d in datos_locales if d[5]==zip_user], key=lambda x:x[2])[:3]
        tablas['local'] = [{
            "description": d[0], "code": d[1], "cash_low": d[2], "cash_high": d[3],
            "insured_low": d[2]*0.8, "insured_high": d[3]*0.85,
            "copay_low": d[2]*0.2, "copay_high": d[3]*0.25,
            "ahorro_seguro": d[2]-d[2]*0.8, "ahorro_copago": d[2]-d[2]*0.2,
            "state": d[4], "county": d[6], "zip_code": d[5]
        } for d in local]

        # Condado
        if tablas['local']:
            county_name = tablas['local'][0]['county']
            county = sorted([d for d in datos_locales if d[6]==county_name], key=lambda x:x[2])[:3]
            tablas['county'] = [{
                "description": d[0], "code": d[1], "cash_low": d[2], "cash_high": d[3],
                "insured_low": d[2]*0.8, "insured_high": d[3]*0.85,
                "copay_low": d[2]*0.2, "copay_high": d[3]*0.25,
                "ahorro_seguro": d[2]-d[2]*0.8, "ahorro_copago": d[2]-d[2]*0.2,
                "state": d[4], "county": d[6], "zip_code": d[5]
            } for d in county]

        # Estado
        if tablas['local']:
            state_name = tablas['local'][0]['state']
            state = sorted([d for d in datos_locales if d[4]==state_name], key=lambda x:x[2])[:3]
            tablas['state'] = [{
                "description": d[0], "code": d[1], "cash_low": d[2], "cash_high": d[3],
                "insured_low": d[2]*0.8, "insured_high": d[3]*0.85,
                "copay_low": d[2]*0.2, "copay_high": d[3]*0.25,
                "ahorro_seguro": d[2]-d[2]*0.8, "ahorro_copago": d[2]-d[2]*0.2,
                "state": d[4], "county": d[6], "zip_code": d[5]
            } for d in state]

        # Nacional
        nacional = sorted(datos_locales, key=lambda x:x[2])[:5]
        tablas['national'] = [{
            "description": d[0], "code": d[1], "cash_low": d[2], "cash_high": d[3],
            "insured_low": d[2]*0.8, "insured_high": d[3]*0.85,
            "copay_low": d[2]*0.2, "copay_high": d[3]*0.25,
            "ahorro_seguro": d[2]-d[2]*0.8, "ahorro_copago": d[2]-d[2]*0.2,
            "state": d[4], "county": d[6], "zip_code": d[5]
        } for d in nacional]

    # ==============================
    # GENERAR HTML
    # ==============================
    html_result = generar_tabla_html(tablas)
    return HTMLResponse(content=html_result)

# ==============================
# STRIPE CHECKOUT
# ==============================
@app.post("/create-checkout-session")
async def checkout(plan: str = Form(...)):
    if plan == "donacion":
        return {"url": LINK_DONACION}

    try:
        mode = "subscription" if plan == "special" else "payment"
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_IDS[plan], "quantity": 1}],
            mode=mode,
            success_url="https://aura-by.onrender.com/?success=true",
            cancel_url="https://aura-by.onrender.com/",
        )
        return {"url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==============================
# LOGIN ADMIN
# ==============================
@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "admin")

    if user == ADMIN_USER and pw == ADMIN_PASS:
        return {"status": "success"}

    return JSONResponse(status_code=401, content={"status": "denied"})
