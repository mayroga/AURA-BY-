import os
import sqlite3
import stripe
import pandas as pd
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def query_low_prices(termino, zip_user):
    try:
        conn = sqlite3.connect('aura_brain.db')
        cur = conn.cursor()
        b = f"%{termino.upper()}%"
        
        # 3 POR ZIP CODE
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE description LIKE ? AND zip_code = ? ORDER BY low_price ASC LIMIT 3", (b, zip_user))
        locales = cur.fetchall()
        
        # 3 POR CONDADO (Primeros 3 dígitos ZIP)
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE description LIKE ? AND zip_code LIKE ? ORDER BY low_price ASC LIMIT 3", (b, f"{zip_user[:3]}%"))
        condado = cur.fetchall()
        
        # 3 POR ESTADO
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE description LIKE ? AND state = (SELECT state FROM prices WHERE zip_code = ?) ORDER BY low_price ASC LIMIT 3", (b, zip_user))
        estado = cur.fetchall()
        
        # 5 NACIONALES (LOS MÁS BARATOS DE LOS 50 ESTADOS)
        cur.execute("SELECT description, low_price, state, zip_code FROM prices WHERE description LIKE ? ORDER BY low_price ASC LIMIT 5", (b,))
        nacionales = cur.fetchall()
        
        # 1 PREMIUM (VALOR DE REFERENCIA ALTO)
        cur.execute("SELECT description, high_price, state, zip_code FROM prices WHERE description LIKE ? ORDER BY high_price DESC LIMIT 1", (b,))
        premium = cur.fetchone()
        
        conn.close()
        return {"zip": locales, "condado": condado, "estado": estado, "nacionales": nacionales, "premium": premium}
    except: return None

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):
    datos = query_low_prices(consulta, zip_user)
    
    prompt = f"""
    ERES AURA, EL ASESOR PROFESIONAL DE MAY ROGA LLC. 
    TU MISIÓN ES AYUDAR AL POBRE Y AL QUE NO TIENE SEGURO A ENCONTRAR EL PRECIO MÁS BAJO EN USA.
    
    CONSULTA: {consulta} | UBICACIÓN: {zip_user} | IDIOMA: {lang}
    DATOS: {datos}

    REGLAS DEL REPORTE:
    1. RESALTA la consulta <span class="res-ask">{consulta}</span> en azul.
    2. ESTRUCTURA (TABLAS O LISTAS): 
       - Presenta 3 precios por ZIP, 3 por Condado, 3 por Estado.
       - Presenta 5 precios NACIONALES (Si el usuario vive en NY y en FL es más barato, ¡DÍSELO!).
       - Presenta 1 opción PREMIUM solo como advertencia de costo elevado.
    3. PRIORIDAD: Siempre busca que el usuario ahorre. Sugiere programas de ayuda si el precio es alto.
    4. TONO: Profesional, directo, experto. No menciones que eres una máquina o software. 
    5. PROHIBIDO: Usar palabras como "IA", "Gobierno" o "Auditoría". 
    6. BLINDAJE: Finaliza con el aviso legal de May Roga LLC.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Asesor de Precios Médicos Profesional."},
                  {"role": "user", "content": prompt}],
        temperature=0.2
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/aclarar-duda")
async def aclarar_duda(pregunta: str = Form(...), contexto: str = Form(...)):
    prompt = f"Como Aura de May Roga LLC, explica esta duda al cliente basándote en su reporte. Reporte: {contexto}. Pregunta: {pregunta}. Sé resolutivo y claro."
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"resultado": response.choices[0].message.content}

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
