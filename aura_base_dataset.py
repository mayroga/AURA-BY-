import sqlite3

DB = "cost_estimates.db"

# --- Lista de 1500 códigos de ejemplo resumidos ---
DATASET = [
    # code, description, low_price, high_price, avg_price, zip_code, state, county
    ("99213", "Consulta Médica General", 75, 150, 112.5, "33101", "FL", "Miami-Dade"),
    ("99214", "Consulta Médica Avanzada", 120, 250, 185, "33101", "FL", "Miami-Dade"),
    ("99203", "Consulta Inicial Adulto", 80, 180, 130, "33101", "FL", "Miami-Dade"),
    ("99204", "Consulta Completa Adulto", 150, 300, 225, "33101", "FL", "Miami-Dade"),
    ("90791", "Evaluación Psicológica", 100, 200, 150, "33101", "FL", "Miami-Dade"),
    ("80053", "Panel de Laboratorio Básico", 50, 120, 85, "33101", "FL", "Miami-Dade"),
    ("85025", "Hemograma Completo", 40, 90, 65, "33101", "FL", "Miami-Dade"),
    ("71020", "Radiografía Torácica", 50, 120, 85, "33101", "FL", "Miami-Dade"),
    ("93000", "Electrocardiograma", 60, 130, 95, "33101", "FL", "Miami-Dade"),
    ("99212", "Consulta Rápida", 60, 120, 90, "33101", "FL", "Miami-Dade"),
    # --- Dental ---
    ("D1110", "Limpieza Dental Básica", 75, 150, 112.5, "33101", "FL", "Miami-Dade"),
    ("D2750", "Corona Dental", 500, 1200, 850, "33101", "FL", "Miami-Dade"),
    ("D4341", "Raspado Subgingival", 150, 400, 275, "33101", "FL", "Miami-Dade"),
    ("D0210", "Radiografía Bitewing", 25, 50, 37.5, "33101", "FL", "Miami-Dade"),
    ("D0330", "Panorámica Dental", 75, 200, 137.5, "33101", "FL", "Miami-Dade"),
]

# --- Generar datos adicionales para simular 1500 códigos ---
import random

estados = ["FL","TX","NY","CA","IL","PA","OH","GA","NC","MI"]
zip_codes = ["33101","75001","10001","90001","60601","19101","44101","30301","27501","48201"]
counties = ["Miami-Dade","Dallas","New York","Los Angeles","Cook","Philadelphia","Cuyahoga","Fulton","Wake","Wayne"]

while len(DATASET) < 1500:
    code = f"{random.randint(90000,99999)}"
    description = f"Procedimiento de Salud {code}"
    low = random.randint(40,200)
    high = low + random.randint(20,400)
    avg = round((low+high)/2,2)
    zipc = random.choice(zip_codes)
    state = random.choice(estados)
    county = random.choice(counties)
    DATASET.append((code, description, low, high, avg, zipc, state, county))

# --- Crear tabla en DB y cargar datos ---
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Tabla principal
cur.execute("""
CREATE TABLE IF NOT EXISTS cost_estimates (
    code TEXT,
    description TEXT,
    low_price REAL,
    high_price REAL,
    avg_price REAL,
    zip_code TEXT,
    state TEXT,
    county TEXT
)
""")

# Tabla precios reportados por usuarios
cur.execute("""
CREATE TABLE IF NOT EXISTS user_prices (
    code TEXT,
    zip_code TEXT,
    state TEXT,
    reported_price REAL,
    note TEXT
)
""")

# Insertar datos
cur.executemany("""
INSERT INTO cost_estimates (code, description, low_price, high_price, avg_price, zip_code, state, county)
VALUES (?,?,?,?,?,?,?,?)
""", DATASET)

conn.commit()
conn.close()
print("✅ DB creada con 1500 códigos y tabla de precios de usuarios lista")
