import sqlite3
import random
import os

DB = "cost_estimates.db"

# --- Crear base de datos resumida de 1500 códigos rápidamente ---
def init_db():
    if os.path.exists(DB):
        print("✅ DB ya existe, se mantiene")
        return

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Tabla principal con 1500 códigos
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

    # Tabla para precios reportados por usuarios
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_prices (
        code TEXT,
        zip_code TEXT,
        state TEXT,
        reported_price REAL,
        note TEXT
    )
    """)

    # Lista base de algunos códigos reales para latinos/seguros baratos
    base_codes = [
        ("99213","Consulta Médica General",75,150,112.5,"33101","FL","Miami-Dade"),
        ("99214","Consulta Médica Avanzada",120,250,185,"33101","FL","Miami-Dade"),
        ("D1110","Limpieza Dental Básica",75,150,112.5,"33101","FL","Miami-Dade"),
        ("D2750","Corona Dental",500,1200,850,"33101","FL","Miami-Dade"),
        ("80053","Panel Laboratorio Básico",50,120,85,"33101","FL","Miami-Dade"),
    ]

    estados = ["FL","TX","NY","CA","IL","PA","OH","GA","NC","MI"]
    zip_codes = ["33101","75001","10001","90001","60601","19101","44101","30301","27501","48201"]
    counties = ["Miami-Dade","Dallas","New York","Los Angeles","Cook","Philadelphia","Cuyahoga","Fulton","Wake","Wayne"]

    DATASET = base_codes.copy()
    while len(DATASET) < 1500:
        code = f"{random.randint(90000,99999)}"
        description = f"Procedimiento Salud {code}"
        low = random.randint(40,200)
        high = low + random.randint(20,400)
        avg = round((low+high)/2,2)
        zipc = random.choice(zip_codes)
        state = random.choice(estados)
        county = random.choice(counties)
        DATASET.append((code,description,low,high,avg,zipc,state,county))

    # Insertar datos
    cur.executemany("""
    INSERT INTO cost_estimates (code, description, low_price, high_price, avg_price, zip_code, state, county)
    VALUES (?,?,?,?,?,?,?,?)
    """, DATASET)

    conn.commit()
    conn.close()
    print("✅ DB creada con 1500 códigos y tabla de precios de usuarios lista")

if __name__ == "__main__":
    init_db()
