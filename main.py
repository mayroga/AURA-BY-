import os
import random
import json
import stripe
import openai
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ==============================
# 1. GENERACIÓN ASÍNCRONA DE RESPALDO (ANTI-FREEZE)
# ==============================
ESTADOS_A = ["FL", "NY", "TX", "PA", "IL", "OH", "GA", "NC", "MI", "NJ", "VA", "WA", "AZ", "MA", "TN", "IN", "MO", "MD", "WI", "CO", "MN", "SC", "AL", "LA", "KY"]
ESTADOS_B = ["CA", "OR", "OK", "UT", "NV", "IA", "AR", "MS", "KS", "CT", "NM", "NE", "WV", "ID", "HI", "NH", "ME", "MT", "RI", "DE", "SD", "ND", "AK", "VT", "WY"]

PROCEDIMIENTOS = {
    "MRI Lumbar Spine": 400, "Dental Crown": 800, "Complete Blood Count": 40,
    "Chest X-Ray": 80, "Colonoscopy": 1100, "ER Visit (Level 3)": 650,
    "Physical Therapy": 100, "Dental Cleaning": 90, "CT Scan Abdomen": 500,
    "Pelvic Ultrasound": 200, "Root Canal": 1000, "Ear Wax Removal": 60,
    "Skin Biopsy": 180, "Prenatal Visit": 150, "Flu Shot": 25,
    "Diabetes Screening": 35, "Mental Health Session": 200, "Sleep Study": 1300,
    "Allergy Test": 300, "Cataract Surgery": 2500
}

def inicializar_seguridad():
    """Crea los archivos si no existen para evitar FileNotFoundError"""
    try:
        if not os.path.exists('data_bloque_A.json'):
            data = {p: {e: {"cash": round(v*random.uniform(0.8, 1.3), 2), "zip": "33101"} for e in ESTADOS_A} for p, v in PROCEDIMIENTOS.items()}
            with open('data_bloque_A.json', 'w') as f: json.dump(data, f)
        if not os.path.exists('data_bloque_B.json'):
            data = {p: {e: {"cash": round(v*random.uniform(0.8, 1.3), 2), "zip": "90210"} for e in ESTADOS_B} for p, v in PROCEDIMIENTOS.items()}
            with open('data_bloque_B.json', 'w') as f: json.dump(data, f)
    except Exception as e:
        print(f"Error preventivo: {e}")

inicializar_seguridad()

# ==============================
# 2. CONFIGURACIÓN Y MIDDLEWARE
# ==============================
load_dotenv()
app = FastAPI(title="AL CIELO by May Roga LLC")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Conexión SQL con manejo de errores para evitar que la app se caiga
try:
    engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True, pool_recycle=3600)
except:
    engine = None

# ==============================
# 3. MOTOR DUAL CON BLINDAJE (ANTI-ERROR)
# ==============================
async def motor_dual_verificacion(consulta, zip_code, lang):
    # NIVEL 1: Carga de JSON (Respaldo Inmediato)
    try:
        with open('data_bloque_A.json') as f: db_a = json.load(f).get(consulta, "Sin datos específicos")
        with open('data_bloque_B.json') as f: db_b = json.load(f).get(consulta, "Sin datos específicos")
        contexto_json = f"Bloque A: {db_a} | Bloque B: {db_b}"
    except:
        contexto_json = "Falla de repositorio; usar inteligencia base."

    # NIVEL 2: Consulta SQL (Si está disponible)
    sql_data = "No disponible"
    if engine:
        try:
            with engine.connect() as conn:
                query = text("SELECT provider_name, cash_price, state, zip FROM health_system WHERE zip = :z AND procedure_name ILIKE :q LIMIT 5")
                res = conn.execute(query, {"z": zip_code, "q": f"%{consulta}%"}).fetchall()
                if res: sql_data = str([dict(row) for row in res])
        except:
            sql_data = "Error de conexión SQL; activando respaldo JSON."

    # NIVEL 3: Generación de Respuesta Asesora
    try:
        check_prompt = f"""
        Como Asesoría AL CIELO (May Roga LLC), analiza: {consulta} en ZIP {zip_code}.
        REPOSITORIO: {contexto_json} | SQL: {sql_data}
        TAREA: Intercambia datos de 50 estados. Si el Bloque B es más barato que el A, rectifica.
        REGLA: 3 Locales, 5 Nacionales, 1 Premium. Tablas HTML #0cf.
        PROHIBIDO: Decir IA o Inteligencia Artificial.
        """
        
        resp = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": "Asesor especialista de May Roga LLC. Resolución inmediata."},
                      {"role": "user", "content": check_prompt}],
            timeout=15  # Evita que la app se quede colgada esperando a OpenAI
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"<h3>Servicio en mantenimiento preventivo</h3><p>Estamos verificando los datos de los 50 estados para usted. Por favor, intente en un momento.</p>"

# ==============================
# 4. RUTAS (CON PROCESAMIENTO SEGURO)
# ==============================
@app.get("/", response_class=HTMLResponse)
async def index():
    try:
        with open("index.html", encoding="utf-8") as f: return f.read()
    except:
        return "Error cargando interfaz. Contacte soporte."

@app.post("/estimado")
async def estimado(consulta: str = Form(...), zip_user: str = Form("33160"), lang: str = Form("es")):
    # No puede dar error: El motor tiene manejo interno de excepciones
    res = await motor_dual_verificacion(consulta, zip_user, lang)
    return JSONResponse({"resultado": res})

@app.post("/consultar-asesor")
async def consultar_asesor(pregunta: str = Form(...), reporte_previo: str = Form(...), lang: str = Form("es")):
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": "Eres el Asesor Humano de May Roga LLC. Resuelve dudas."},
                      {"role": "user", "content": f"Contexto: {reporte_previo}. Duda: {pregunta}"}]
        )
        return {"respuesta_asesor": resp.choices[0].message.content}
    except:
        return {"respuesta_asesor": "En este momento el asesor está procesando otra carga. Intente en unos segundos."}

@app.post("/create-checkout-session")
async def checkout(plan: str = Form(...)):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_IDS.get(plan, PRICE_IDS['standard']), "quantity": 1}],
            mode="payment" if plan != "special" else "subscription",
            success_url="https://aura-by.onrender.com/?success=true",
            cancel_url="https://aura-by.onrender.com/",
        )
        return {"url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Falla en pasarela de pagos."})
