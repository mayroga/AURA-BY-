import os, sqlite3, stripe, openai
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw"
}

def query_aura_brain(termino, zip_user):
    conn = sqlite3.connect('aura_brain.db')
    cur = conn.cursor()
    b = f"%{termino.upper()}%"
    
    # 3 Locales
    cur.execute("SELECT description, low_price, high_price, state, zip_code FROM prices WHERE (description LIKE ? OR cpt_code LIKE ?) AND zip_code = ? LIMIT 3", (b, b, zip_user))
    locales = cur.fetchall()
    
    # 3 Condado/Estado
    cur.execute("SELECT description, low_price, high_price, state, zip_code FROM prices WHERE (description LIKE ? OR cpt_code LIKE ?) AND state = (SELECT state FROM prices WHERE zip_code = ? LIMIT 1) LIMIT 3", (b, b, zip_user))
    condado = cur.fetchall()

    # 5 Nacionales (Los más baratos del país)
    cur.execute("SELECT description, low_price, high_price, state, zip_code FROM prices WHERE (description LIKE ? OR cpt_code LIKE ?) ORDER BY low_price ASC LIMIT 5", (b, b))
    nacionales = cur.fetchall()
    
    conn.close()
    return {"locales": locales, "condado": condado, "nacionales": nacionales}

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):
    datos = query_aura_brain(consulta, zip_user)
    
    prompt = f"""
    ERES AURA BY MAY ROGA LLC. Tu misión es educar sobre precios médicos en USA.
    USA TABLAS HTML CLARAS PARA LOS RESULTADOS.
    
    ESTRUCTURA DE RESPUESTA REQUERIDA:
    1. Tabla '3 PRECIOS MÁS BAJOS EN TU ZIP {zip_user}'.
    2. Tabla '3 OPCIONES EN TU CONDADO/ESTADO'.
    3. Tabla '5 OPCIONES DE AHORRO NACIONAL (ZIP, ESTADO, PRECIO)'.
    4. Tabla '1 OPCIÓN PREMIUM/LUJO'.
    
    DATOS REALES: {datos}
    CONSULTA DEL CLIENTE: {consulta}
    
    REGLAS:
    - Compara Precio CASH vs Seguro (Estima el deducible).
    - No menciones que eres una IA. Habla como Asesor Experto.
    - Si no hay datos exactos, usa tu conocimiento de CMS/United Healthcare para estimar.
    - Finaliza con: 'Sugerencia informativa. No es una orden médica.'
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/aclarar-duda")
async def aclarar_duda(pregunta: str = Form(...), contexto: str = Form(...)):
    # PROTOCOLO DE ASESORÍA PERSONALIZADA (Solo para clientes Pagados)
    prompt = f"Como Asesor Senior de AURA, aclara de forma profesional la siguiente duda del cliente sobre el reporte anterior: {pregunta}. Contexto del reporte: {contexto}. Sé técnico pero comprensible."
    
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"resultado": response.choices[0].message.content}

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f: return f.read()

# ... (Mantener funciones de Stripe y Login Admin igual que en tu versión previa)
