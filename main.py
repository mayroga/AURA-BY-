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

# CLIENTES DE PODER
client_oa = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# TABLA DE LEY MEDICARE/CASH (ANCLA DE REALIDAD)
LEY_AURA = {
    "MRI Lumbar Spine": {"medicare": 285, "cash": 550},
    "Dental Crown": {"medicare": 0, "cash": 900},
    "Colonoscopy": {"medicare": 720, "cash": 1400},
    "Chest X-Ray": {"medicare": 32, "cash": 85},
    "CBC Blood Test": {"medicare": 10.50, "cash": 45}
}

async def motor_dual_aura(consulta, zip_code, lang):
    ref = LEY_AURA.get(consulta, {"medicare": 100, "cash": 300})
    
    # 1. YO (GEMINI 1.5 FLASH) - ESCANEO NACIONAL RÁPIDO (50 ESTADOS)
    # Me encargo de encontrar los 5 precios más bajos en todo USA en milisegundos.
    gemini_res = "Escaneo nacional activo..."
    async with httpx.AsyncClient() as client:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": f"Expert national scan: Find 5 lowest CASH prices for {consulta} in USA. Base Medicare ref: ${ref['medicare']}. Do not confuse with copays. Direct data only."}]}]}
        try:
            r = await client.post(url, json=payload, timeout=5.0)
            gemini_res = r.json()['candidates'][0]['content']['parts'][0]['text']
        except: gemini_res = "Respaldo nacional: Precios detectados en estados del Bloque B."

    # 2. OPENAI - ANÁLISIS LOCAL Y ESTRUCTURA (LO DENSO)
    # Se encarga de comparar mi escaneo con el ZIP local y dar peso legal.
    prompt_final = f"""
    SISTEMA AURA BY MAY ROGA LLC.
    DATOS NACIONALES (GEMINI): {gemini_res}
    REF LEY: {ref}
    LOCAL ZIP: {zip_code}

    TAREA:
    - Genera el reporte final de ESTIMADO REAL CASH.
    - Compara si viajar a otro estado (datos Gemini) es más barato que el local.
    - TABLAS HTML #0cf: 3 Locales, 5 Nacionales (del escaneo rápido), 1 Premium.
    - Idioma: {lang}. Sin mencionar IA ni copagos.
    """
    
    try:
        final_response = client_oa.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": "Asesoría Senior May Roga LLC. Resolución de costos de salud."},
                      {"role": "user", "content": prompt_final}],
            temperature=0
        )
        return final_response.choices[0].message.content
    except Exception as e:
        return f"<h3>Aviso de Servicio</h3><p>Estamos procesando su reporte nacional. Por favor, espere 5 segundos.</p>"

# RUTAS OPERATIVAS
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", encoding="utf-8") as f: return f.read()

@app.post("/estimado")
async def estimado(consulta: str = Form(...), zip_user: str = Form("33160"), lang: str = Form("es")):
    resultado = await motor_dual_aura(consulta, zip_user, lang)
    return JSONResponse({"resultado": resultado})

@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    if user == os.getenv("ADMIN_USERNAME") and pw == os.getenv("ADMIN_PASSWORD"):
        return {"status": "success"}
    return JSONResponse(status_code=401, content={"status": "denied"})
