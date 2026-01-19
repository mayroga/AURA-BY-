import os
import sqlite3
import stripe
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse
import openai
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

def query_sql_aura(termino, zip_user):
    try:
        conn = sqlite3.connect('aura_brain.db')
        cur = conn.cursor()
        search = f"%{termino.upper()}%"
        
        # 3 LOCALES
        cur.execute("SELECT * FROM costs WHERE desc LIKE ? AND zip = ? LIMIT 3", (search, zip_user))
        locales = cur.fetchall()
        
        # 5 NACIONALES (Más bajos)
        cur.execute("SELECT * FROM costs WHERE desc LIKE ? ORDER BY price_low ASC LIMIT 5", (search,))
        nacionales = cur.fetchall()
        
        # 1 PREMIUM (Más caro)
        cur.execute("SELECT * FROM costs WHERE desc LIKE ? ORDER BY price_high DESC LIMIT 1", (search,))
        premium = cur.fetchone()
        
        conn.close()
        return {"locales": locales, "nacionales": nacionales, "premium": premium}
    except:
        return None

@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("en"), zip_user: str = Form(None)):
    datos_mercado = query_sql_aura(consulta, zip_user)
    
    prompt = f"""
    ERES AURA, ASESOR PROFESIONAL DE MAY ROGA LLC. 
    ESTÁS GENERANDO UN REPORTE DE MERCADO PARA UN CLIENTE QUE PAGÓ POR INFORMACIÓN.
    
    CONSULTA: {consulta}
    ZIP: {zip_user}
    DATOS SQL: {datos_mercado}

    ESTRUCTURA OBLIGATORIA (USA HTML):
    1. Resaltar la consulta en AZUL NEÓN.
    2. TABLA DE 3 PRECIOS LOCALES (Cerca de {zip_user}).
    3. TABLA DE 5 PRECIOS NACIONALES (Los más baratos de USA para demostrar ahorro).
    4. OPCIÓN PREMIUM (La más costosa de referencia).
    5. COMPARATIVA: CASH PRICE vs ESTIMATED INSURANCE.
    
    REGLAS:
    - NO USAR PÁRRAFOS. Solo tablas y listas.
    - NO MENCIONAR 'IA', 'ALGORITMO', ni 'GOBIERNO'.
    - Si faltan datos en SQL, completa con el estándar del health system de los 50 estados (CMS).
    - Idioma: {lang}
    - Termina con el BLINDAJE LEGAL de May Roga LLC.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are Aura, a professional price transparency expert."},
                  {"role": "user", "content": prompt}],
        temperature=0.2
    )
    return {"resultado": response.choices[0].message.content}

@app.post("/aclarar-duda")
async def aclarar_duda(pregunta: str = Form(...), contexto: str = Form(...)):
    # El cliente paga por este servicio, respuesta experta y resolutiva.
    prompt = f"Como Aura (May Roga LLC), aclara esta duda técnica del cliente basándote en este reporte: {contexto}. Pregunta: {pregunta}."
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"resultado": response.choices[0].message.content}

# ... Resto de rutas de Stripe y Admin ...
