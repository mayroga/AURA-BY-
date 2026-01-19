import csv
import random
import sqlite3
import os

# --- Configuración ---
FILENAME = "aura_cms_core.csv"
DB = "cost_estimates.db"

STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
          "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
          "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
          "VA","WA","WV","WI","WY"]

BASE_PROCS = [
    ("99213","Consulta médica general","Medical",95.0),
    ("99214","Consulta médica intermedia","Medical",140.0),
    ("70551","Resonancia Magnética MRI","Imaging",1100.0),
    ("70450","Tomografía Computarizada CT","Imaging",450.0),
    ("93000","Electrocardiograma EKG","Diagnostic",50.0),
    ("D1110","Limpieza dental","Dental",135.0),
    ("D1120","Profilaxis dental niños","Dental",120.0),
    ("D2740","Corona dental","Dental",1250.0),
    ("D2330","Resina simple anterior","Dental",250.0),
    ("D2391","Resina compuesta posterior","Dental",300.0),
]

TOTAL_CODES = 1500
ROWS = []

# --- Generar filas ---
for i in range(TOTAL_CODES):
    base = random.choice(BASE_PROCS)
    code, desc, cat, base_price = base
    state = random.choice(STATES)
    zip_code = str(random.randint(10001, 99950))
    
    # Precios con factor por estado
    state_factor = random.uniform(0.9,1.3)
    avg_price = round(base_price * state_factor, 2)
    low_price = round(avg_price * 0.75, 2)
    high_price = round(avg_price * 1.35, 2)
    
    ROWS.append([code, desc, cat, zip_code, "County", state, low_price, avg_price, high_price, "Estimated"])

# --- Guardar CSV ---
with open(FILENAME,"w",newline="",encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["code","description","category","zip_code","county","state","low_price","avg_price","high_price","source"])
    writer.writerows(ROWS)
print(f"✅ {FILENAME} generado con {TOTAL_CODES} códigos de ejemplo")

# --- Crear SQLite DB ---
if os.path.exists(DB):
    os.remove(DB)

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("""
CREATE TABLE cost_estimates (
    code TEXT,
    description TEXT,
    category TEXT,
    zip_code TEXT,
    county TEXT,
    state TEXT,
    low_price REAL,
    avg_price REAL,
    high_price REAL,
    source TEXT
)
""")

with open(FILENAME,"r",encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cur.execute("""
        INSERT INTO cost_estimates (code, description, category, zip_code, county, state, low_price, avg_price, high_price, source)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            row['code'], row['description'], row['category'], row['zip_code'], row['county'], row['state'],
            float(row['low_price']), float(row['avg_price']), float(row['high_price']), row['source']
        ))
con.commit()
con.close()
print(f"✅ {DB} creado y llenado automáticamente con {TOTAL_CODES} códigos")
