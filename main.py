import os
import sqlite3
import stripe
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Configuración de Claves
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw",
    "donacion": "price_1SnatfBOA5mT4t0PZouWzfpw" # O tu ID de donación
}

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def query_sql_3351(termino, zip_user=None):
    """Lógica para extraer datos según la regla 3-3-5-1"""
    try:
        conn = sqlite3.connect('cost_estimates.db')
        cur = conn.cursor()
        b = f"%{termino.upper()}%"
        
        # 3 LOCALES (ZIP)
        cur.execute("SELECT provider, city, low_price, high_price FROM cost_estimates WHERE description LIKE ? AND zip_code = ? LIMIT 3", (b, zip_user))
        locales = cur.fetchall()
        
        # 5 NACIONALES (Más Bajos)
        cur.execute("SELECT provider, state, low_price FROM cost_estimates WHERE description LIKE ? ORDER BY low_price ASC LIMIT 5", (b,))
        nacionales = cur.fetchall()
        
        # 1 PREMIUM
        cur.execute("SELECT provider, high_price FROM cost_estimates WHERE description LIKE ? ORDER BY high_price DESC LIMIT 1", (b,))
        premium = cur.fetchone()
        
        conn.close()
        return {"locales": locales, "nacionales": nacionales, "premium": premium}
    except:
        return None

@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    try:
        price_id = PRICE_IDS.get(plan)
        if not price_id: raise HTTPException(status_code=400)

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='payment',
            success_url="https://tu-dominio.com/?success=true",
            cancel_url="https://tu-dominio.com/?cancel=true",
        )
        return {"id": session.id}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("en"), zip_user: str = Form(None)):
    datos_sql = query_sql_3351(consulta, zip_user)
    
    # PROMPT DE EXPERTO - SIN PALABRAS PROHIBIDAS
    prompt = f"""
    YOU ARE AURA, THE EXPERT ADVISOR FROM MAY ROGA LLC.
    YOUR CLIENT PAID FOR A PREMIUM MARKET REPORT.
    
    TASK: Provide a comparative medical/dental price report for: {consulta} in ZIP {zip_user}.
    LANGUAGE: Strictly respond in {lang}. 
    (If 'en' use English, if 'es' use Spanish, if 'ht' use Haitian Creole).

    MANDATORY STRUCTURE (Use HTML):
    1. HEADER: Procedure name in Large Blue.
    2. THE 3-3-5-1 RULE:
       - 3 LOCAL OPTIONS (Cerca de {zip_user}).
       - 3 STATE/COUNTY OPTIONS.
       - 5 NATIONAL LOWEST PRICE OPTIONS (The 'Smart Savings' picks).
       - 1 PREMIUM OPTION (Luxury/High-end).
    3. PRICE COMPARISON: Show Cash Price vs. Estimated Insurance Rate for each.
    4. SAVINGS ADVICE: Propose why choosing a national low-cost option is a smart financial move.

    CRITICAL CONSTRAINTS:
    - DO NOT mention 'IA', 'Artificial Intelligence', or 'Government'.
    - DO NOT use paragraphs. Use Tables, Bullet points, and bold headers.
    - Be professional, advisory, and authoritative in market data.
    - Reference Data: {datos_sql} (If null, use your CMS market knowledge to estimate Fair Prices).
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/aclarar-duda")
async def aclarar_duda(pregunta: str = Form(...), contexto: str = Form(...), lang: str = Form("en")):
    prompt = f"The client has a doubt about this Aura report: {contexto}. Question: {pregunta}. Answer in {lang} as the Aura Expert."
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    # Acceso Gratuito con tus credenciales
    if user == "NAME" and pw == "CLAVE":
        return {"status": "ok"}
    return JSONResponse(status_code=401, content={"error": "Invalid"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
