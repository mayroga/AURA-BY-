import os
import random
import stripe
import httpx  # Para Gemini sin usar google-generativeai
from openai import OpenAI
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="AURA BY MAY ROGA LLC")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Clientes de IA
client_oa = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# 1. REFERENCIA MAESTRA (CASH VS MEDICARE) - NO COPAGOS
REFERENCIA_EXPERTA = {
    "MRI Lumbar Spine": {"medicare": 285, "cash_avg": 550, "premium": 1500},
    "Dental Crown": {"medicare": 0, "cash_avg": 900, "premium": 2500},
    "Colonoscopy": {"medicare": 720, "cash_avg": 1400, "premium": 4000}
}

async def motor_dual_expert(consulta, zip_code, lang):
    ref = REFERENCIA_EXPERTA.get(consulta, {"medicare": 100, "cash_avg": 300, "premium": 1000})
    
    # Unidad A (OpenAI) - Análisis de Mercado Este
    prompt_oa = f"Analiza precio CASH (no copago) para {consulta} en ZIP {zip_code}. Ref Medicare: ${ref['medicare']}. Da 3 opciones locales."
    res_oa = client_oa.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt_oa}]
    ).choices[0].message.content

    # Unidad B (Gemini vía HTTP directo - Sin google-generativeai)
    # Google procesa la petición general sin clasificaciones
    res_gem = "Unidad B en espera"
    async with httpx.AsyncClient() as client:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": f"Expert price analysis for {consulta} in USA. Compare National Cash Prices vs Medicare ${ref['medicare']}. Be specific and direct."}]}]}
        try:
            r = await client.post(url, json=payload)
            res_gem = r.json()['candidates'][0]['content']['parts'][0]['text']
        except: res_gem = "Análisis nacional de respaldo activo."

    # Fusión de Resultados (AURA BY MAY ROGA LLC)
    # Aquí se elimina la confusión de copagos y se da el estimado para TODOS
    prompt_final = f"""
    Actúa como el cerebro de AURA BY MAY ROGA LLC. 
    DATOS UNIDAD A: {res_oa}
    DATOS UNIDAD B: {res_gem}
    REFERENCIA LEY: {ref}

    TAREA: Crea un reporte de ESTIMADO REAL (CASH).
    - Ignora copagos de seguros. El cliente busca el precio de mercado para ahorrar, incluso viajando a otro estado.
    - Compara el ahorro nacional vs local.
    - Estructura: Tabla HTML #0cf (3 Locales, 5 Nacionales más baratos, 1 Premium).
    - Idioma: {lang}. Prohibido decir IA.
    """
    
    final = client_oa.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "Asesor de Peso en Salud USA. No usas lenguaje de IA."},
                  {"role": "user", "content": prompt_final}]
    ).choices[0].message.content
    return final

# 2. RUTAS
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", encoding="utf-8") as f: return f.read()

@app.post("/estimado")
async def estimado(consulta: str = Form(...), zip_user: str = Form("33160"), lang: str = Form("es")):
    resultado = await motor_dual_expert(consulta, zip_user, lang)
    return JSONResponse({"resultado": resultado})

@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if user == os.getenv("ADMIN_USERNAME") and pw == os.getenv("ADMIN_PASSWORD"):
        return {"status": "success"}
    return JSONResponse(status_code=401, content={"status": "denied"})
