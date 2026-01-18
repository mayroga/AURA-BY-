import os
import sqlite3
import stripe
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
from dotenv import load_dotenv
import requests
import pandas as pd
from datetime import datetime

load_dotenv()
app = FastAPI()

# ==============================
# Configuración Stripe & IA
# ==============================
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

client_gemini = None
gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    try:
        from google import genai
        client_gemini = genai.Client(api_key=gemini_api_key)
    except Exception as e:
        print(f"[WARNING] Gemini no inicializado: {e}")
else:
    print("[WARNING] GEMINI_API_KEY no encontrada, Gemini deshabilitado.")

openai.api_key = os.getenv("OPENAI_API_KEY")

PRICE_IDS = {
    "rapido": "price_1Snam1BOA5mT4t0PuVhT2ZIq",
    "standard": "price_1SnaqMBOA5mT4t0PppRG2PuE",
    "special": "price_1SnatfBOA5mT4t0PZouWzfpw"
}
LINK_DONACION = "https://buy.stripe.com/28E00igMD8dR00v5vl7Vm0h"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ==============================
# Funciones SQL y CMS Public Data
# ==============================
def ingest_cms_data():
    conn = sqlite3.connect("aura_brain.db")
    CMS_DATASETS = {
        "physician_fee": "https://data.cms.gov/resource/7b3x-3k6u.csv?$limit=50000",
        "outpatient": "https://data.cms.gov/resource/9wzi-peqs.csv?$limit=50000"
    }

    for name, url in CMS_DATASETS.items():
        try:
            print(f"Descargando dataset {name}...")
            df = pd.read_csv(url)
            df.columns = [c.lower() for c in df.columns]
            keep = [c for c in df.columns if c in ["hcpcs_code","cpt_code","payment_amount","state","locality"]]
            df = df[keep]
            df["source"] = name
            df["ingested_at"] = datetime.utcnow()
            df.to_sql("government_prices", conn, if_exists="append", index=False)
        except Exception as e:
            print(f"[ERROR INGESTA {name}] {e}")
    conn.close()
    print("✔ CMS data ingested")

def get_estimated_price(code, state):
    conn = sqlite3.connect("aura_brain.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT AVG(payment_amount), MIN(payment_amount), MAX(payment_amount)
        FROM government_prices
        WHERE (hcpcs_code=? OR cpt_code=?) AND state=?
    """, (code, code, state))
    row = cur.fetchone()
    conn.close()
    if not row or row[0] is None:
        return None
    avg, min_p, max_p = row
    return {"average": round(avg,2), "min": round(min_p,2), "max": round(max_p,2)}

def dental_fair_price(low, high):
    return {"fair_min": round(low*0.9,2), "fair_max": round(high*1.1,2)}

# ==============================
# Función SQL local
# ==============================
def query_sql(termino, zip_user=None):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'cost_estimates.db')
        if not os.path.exists(db_path):
            return "SQL_OFFLINE"

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        busqueda = f"%{termino.strip().upper()}%"
        cursor.execute("""
        SELECT cpt_code, description, state, zip_code, low_price, high_price
        FROM cost_estimates
        WHERE description LIKE ? OR cpt_code LIKE ?
        ORDER BY low_price ASC
        LIMIT 20
        """, (busqueda, busqueda))
        results = cursor.fetchall()
        conn.close()
        if not results:
            return "DATO_NO_SQL"

        local, county, state_list, national = [], [], [], []
        for r in results:
            code, desc, state_r, zip_r, low, high = r
            if zip_user and zip_r == zip_user:
                local.append(r)
            elif zip_user and zip_r.startswith(zip_user[:3]):
                county.append(r)
            elif zip_user and state_r == zip_user[:2]:
                state_list.append(r)
            else:
                national.append(r)

        return {"local": local[:3], "county": county[:3], "state": state_list[:3], "national": national[:5]}

    except Exception as e:
        print(f"[ERROR SQL] {e}")
        return f"ERROR_SQL: {str(e)}"

# ==============================
# Ruta principal
# ==============================
@app.get("/", response_class=HTMLResponse)
async def read_index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

# ==============================
# Obtener estimado educativo dental
# ==============================
@app.post("/estimado")
async def obtener_estimado(consulta: str = Form(...), lang: str = Form("es"), zip_user: str = Form(None)):
    ingest_cms_data()  # Actualiza CMS al llamar la ruta
    datos_sql = query_sql(consulta, zip_user)

    # Generar tabla educativa dental
    tabla_dental = f"""
1️⃣ PRECIOS POR UBICACIÓN (ZIP CODES)
Servicio\tZIP Code Ejemplo\tPrecio CASH\tPrecio con Seguro\tGoogle Maps
Limpieza dental\t33125\t$50 – $120\t$20 – $60\thttps://www.google.com/maps/search/?api=1&query=33125
Limpieza dental\t33130\t$55 – $130\t$25 – $65\thttps://www.google.com/maps/search/?api=1&query=33130
Empaste simple\t33125\t$150 – $400\t$60 – $200\thttps://www.google.com/maps/search/?api=1&query=33125
Empaste simple\t33130\t$160 – $420\t$70 – $220\thttps://www.google.com/maps/search/?api=1&query=33130
Corona dental\t33125\t$500 – $2,000\t$200 – $900\thttps://www.google.com/maps/search/?api=1&query=33125
Corona dental\t33130\t$520 – $2,100\t$220 – $950\thttps://www.google.com/maps/search/?api=1&query=33130

💡 Nota: Los ZIP codes se usan como referencia para localizar áreas con precios más accesibles. No se mencionan clínicas privadas por razones legales.

2️⃣ PRECIOS POR CONDADO – MIAMI-DADE
Limpieza dental: $45 – $340
Empaste simple: $140 – $590
Corona dental: $480 – $2,950

3️⃣ PRECIOS POR ESTADO – FLORIDA
Limpieza dental: $40 – $330
Empaste simple: $130 – $580
Corona dental: $470 – $2,900

4️⃣ PRECIOS NACIONALES
Limpieza dental: $30 – $300
Empaste simple: $120 – $550
Corona dental: $450 – $2,800

5️⃣ OPCIONES GRATUITAS O MUY ACCESIBLES
Tipo de Servicio\tClínicas / Organizaciones\tCómo acceder
Limpieza y chequeo básico\tCommunity Health Centers (CHC) – Miami\tRegistro como paciente, demostración de ingresos bajos
Empaste básico\tNeighborhood Health Clinics\tLlamar y solicitar programa de asistencia dental
Corona dental de emergencia\tSalud Dental Miami\tSolo casos de emergencia, cita previa obligatoria

✅ Recomendación: Llama con anticipación y pregunta por “programa de asistencia para bajos ingresos” o “sliding scale fees” para conocer si calificas.

6️⃣ COMPARACIÓN CASH vs ASEGURO
Muchos pacientes con seguro ahorran entre 30% – 70% según cobertura y deducible.
Algunos tratamientos pueden ser más económicos pagando en efectivo.
Copagos pueden aplicar para seguros, mientras clínicas de asistencia solo piden prueba de ingresos.

7️⃣ CONSEJOS PRÁCTICOS
- Compara precios por ZIP code antes de elegir dónde ir.
- Limpiezas rutinarias más baratas en clinics comunitarias o áreas de bajos ingresos.
- Pregunta por pago en efectivo o programas de sliding scale.
- Servicios urgentes o coronas: revisar hospitales con asistencia dental gratuita.
"""

    # Integración con IA (Gemini/OpenAI) para generar texto educativo adicional
    prompt = f"""
ERES AURA, MOTOR DE ESTIMADOS DE PRECIOS MÉDICOS Y DENTALES.
DATOS SQL: {datos_sql}
ZIP DETECTADO: {zip_user}
OBJETIVO: Mostrar reporte educativo dental con ZIP codes, condado, estado, cash vs seguro, clínicas gratuitas y mapa Google.
Mostrar todo en {lang}.
"""
    motores = []
    if client_gemini:
        try:
            modelos_gemini = client_gemini.models.list().data
            if modelos_gemini:
                motores.append(("gemini", modelos_gemini[0].name))
        except: pass
    motores.append(("openai", "gpt-4"))

    for motor, modelo in motores:
        try:
            if motor == "gemini" and client_gemini:
                response = client_gemini.models.generate_content(model=modelo, contents=prompt)
                ai_text = response.text
                break
            elif motor == "openai":
                response = openai.chat.completions.create(
                    model=modelo,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                )
                ai_text = response.choices[0].message.content
                break
        except:
            ai_text = ""
            continue

    resultado_final = tabla_dental + "\n\n" + (ai_text or "")

    return {"resultado": resultado_final}

# ==============================
# Crear sesión Stripe
# ==============================
@app.post("/create-checkout-session")
async def create_checkout(plan: str = Form(...)):
    if plan.lower() == "donacion":
        return {"url": LINK_DONACION}
    try:
        mode = "subscription" if plan.lower() == "special" else "payment"
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_IDS[plan.lower()], "quantity": 1}],
            mode=mode,
            success_url="https://aura-by.onrender.com/?success=true",
            cancel_url="https://aura-by.onrender.com/"
        )
        return {"url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==============================
# Login Admin / Acceso gratuito
# ==============================
@app.post("/login-admin")
async def login_admin(user: str = Form(...), pw: str = Form(...)):
    ADMIN_USER = os.getenv("ADMIN_USERNAME", "TU_USERNAME")
    ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "TU_PASSWORD")
    if user == ADMIN_USER and pw == ADMIN_PASS:
        return {"status": "success", "access": "full"}
    return JSONResponse(status_code=401, content={"status": "error"})
