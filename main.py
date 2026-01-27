import os
import random
import stripe
import httpx
from openai import OpenAI
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="AURA BY MAY ROGA LLC")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

client_oa = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# TABLA DE LEY: MEDICARE (Piso), MEDICAID (Social), CASH (Realidad), PREMIUM (Abuso)
TABLA_EXPERTA = {
    "MRI Lumbar Spine": {"cpt": "72148", "medicare": 285, "medicaid": 190, "cash_low": 450, "premium": 1500},
    "Dental Crown": {"cpt": "D2740", "medicare": 0, "medicaid": 450, "cash_low": 850, "premium": 2500},
    "Colonoscopy": {"cpt": "45378", "medicare": 720, "medicaid": 510, "cash_low": 1150, "premium": 4500}
}

async def motor_contraste_aura(consulta, zip_code, lang):
    ref = TABLA_EXPERTA.get(consulta, {"medicare": 100, "cash_low": 300, "premium": 1000})
    
    # 1. ESCANEO VELOZ (GEMINI): LA REALIDAD NACIONAL (50 ESTADOS)
    # Busca los precios reales más bajos por condado/estado en milisegundos.
    async with httpx.AsyncClient() as client:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": f"Busca el precio CASH REAL más bajo en USA para {consulta}. Compara estados baratos (Texas/Florida) vs caros (NY/CA). Usa el ancla Medicare: ${ref['medicare']}."}]}]}
        try:
            r = await client.post(url, json=payload, timeout=5.0)
            datos_nacionales = r.json()['candidates'][0]['content']['parts'][0]['text']
        except: datos_nacionales = "Error de conexión en Unidad B."

    # 2. ANÁLISIS DE PESO (OPENAI): EL JUEGO DE LA VERDAD VS EL DESEO
    # Aquí es donde se comporta como experto e inexperto a la vez.
    prompt_final = f"""
    SISTEMA AURA BY MAY ROGA LLC. 
    Consulta: {consulta} | ZIP: {zip_code}
    DATOS NACIONALES: {datos_nacionales}
    REFERENCIA EXPERTA: {ref}

    INSTRUCCIÓN DE EXPERTO:
    1. LA "MENTIRA DESEADA": Menciona lo que los seguros/copagos dicen (lo que todos quieren oír) pero advierte que es una ilusión.
    2. LA "REALIDAD CRUDA": Da el precio CASH más bajo encontrado en USA y el más caro (Premium).
    3. CONTRASTE: Muestra el precio por ZIP/Condado local vs. el mejor precio por Estado nacional.
    4. FORMATO: Tabla HTML #0cf. 
       - Columna 1: Opción "Deseada" (Seguros/Copagos - La Mentira).
       - Columna 2: Opción "Real Cash" (La Verdad).
       - Columna 3: Ahorro Real si viaja.
    
    Idioma: {lang}. Sin decir IA. Sé directo, ten mucho peso.
    """
    
    try:
        final_response = client_oa.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": "Cerebro de AURA. Diferencias entre la ilusión del copago y la verdad del mercado Cash."},
                      {"role": "user", "content": prompt_final}],
            temperature=0
        )
        return final_response.choices[0].message.content
    except Exception as e:
        return f"Error en reporte: {str(e)}"

@app.post("/estimado")
async def estimado(consulta: str = Form(...), zip_user: str = Form("33160"), lang: str = Form("es")):
    resultado = await motor_contraste_aura(consulta, zip_user, lang)
    return JSONResponse({"resultado": resultado})

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", encoding="utf-8") as f: return f.read()

@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if user == os.getenv("ADMIN_USERNAME") and pw == os.getenv("ADMIN_PASSWORD"):
        return {"status": "success"}
    return JSONResponse(status_code=401, content={"status": "denied"})
