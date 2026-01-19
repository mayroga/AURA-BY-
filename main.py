import os, sqlite3, stripe
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/", response_class=HTMLResponse)
def index():
    return open("index.html",encoding="utf-8").read()

@app.post("/create-checkout-session")
def checkout(price_id: str = Form(...)):
    s = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url="https://aura.mayroga.com/success",
        cancel_url="https://aura.mayroga.com"
    )
    return {"url": s.url}

@app.post("/estimado")
def estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form("")):

    prompt=f"""
RESPONDE EXCLUSIVAMENTE EN {lang.upper()}.

GENERA ESTE FORMATO EXACTO:

REPORTE AURA
────────────
• Procedimiento / Servicio consultado: {consulta}
• Ubicación (ZIP): {zip_user}

• OPCIONES LOCALES MÁS BARATAS (TOP 3)
• OPCIONES NACIONALES MÁS BARATAS (TOP 5)
• OPCIÓN PREMIUM
• COMPARACIÓN CASH VS INSURANCE
• PRECIO JUSTO (FAIR PRICE)
• AHORRO REAL
• DIAGNÓSTICO DE MERCADO
• CIERRE DE AUTORIDAD

USA HTML LIMPIO.
NO MENCIONES IA.
"""

    r=client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"user","content":prompt}],
        temperature=0.25
    )
    return {"resultado":r.choices[0].message.content}
