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

# IDs de Stripe ACTUALIZADOS
PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw"
}

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def query_aura_brain(termino, zip_user):
    try:
        conn = sqlite3.connect('aura_brain.db')
        cur = conn.cursor()
        b = f"%{termino.upper()}%"
        
        # Búsqueda 3 Locales
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE (description LIKE ? OR cpt_code LIKE ?) AND zip_code = ? LIMIT 3", (b, b, zip_user))
        locales = cur.fetchall()
        
        # Búsqueda 5 Nacionales más baratos
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE (description LIKE ? OR cpt_code LIKE ?) ORDER BY low_price ASC LIMIT 5", (b, b))
        nacionales = cur.fetchall()
        
        conn.close()
        return {"locales": locales, "nacionales": nacionales}
    except: return None

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("en"), zip_user: str = Form(None)):
    datos_sql = query_aura_brain(consulta, zip_user)
    
    prompt = f"""
    YOU ARE AURA BY MAY ROGA LLC. Professional Health Advisory Expert.
    MANDATE: Provide a clear price comparison. Use HTML TABLES ONLY. No text blocks.
    
    STRUCTURE 3-3-5-1:
    1. TABLE 1: "3 Lowest Nearby (ZIP {zip_user})". Columns: ZIP, County, State, Est. Cash Price.
    2. TABLE 2: "3 Regional/State Savings". Columns: ZIP, County, State, Est. Cash Price.
    3. TABLE 3: "5 National Maximum Savings". Columns: ZIP, County, State, Est. Cash Price.
    4. HIGHLIGHT: "1 Premium/Luxury Reference Option".
    
    DATA SOURCE: Use SQL Data: {datos_sql}. If empty, use your internal expertise from CMS (Medicare Fee Schedule), FAIR Health, and ADA for 2026.
    
    LEGAL RULES: 
    - Use terms: "Suggested Estimate", "Advisory Proposal".
    - Never say "AI" or "Government Order".
    - Show "Cash Price" vs "Estimated Insurance Price" (approx 30-40% of cash).
    - Language: {lang}.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/aclarar-duda")
async def aclarar_duda(consulta: str = Form(...), lang: str = Form("en")):
    # PROTOCOLO DE ASESOR PARA CLIENTES DE PAGO
    prompt = f"""
    The customer has paid for professional clarification. 
    Question: {consulta}
    Language: {lang}
    Response Style: Highly professional, empathetic, and advisory. Explain the difference between CPT/CDT codes, why prices vary by ZIP code, and how they can negotiate with the clinic using this report.
    Safety: Remind them this is for educational purposes and they should show this report to their provider.
    """
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": PRICE_IDS[plan], "quantity": 1}],
        mode="payment",
        success_url="https://aura-by.onrender.com/?success=true",
        cancel_url="https://aura-by.onrender.com/"
    )
    return {"url": session.url}

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f: return f.read()
