import csv
import random

# Nombre del archivo final
FILENAME = "aura_cms_core.csv"

# Lista de 50 estados
STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
          "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
          "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
          "VA","WA","WV","WI","WY"]

# Procedimientos de ejemplo comprimidos (podríamos generar 1500 variando estos)
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

TOTAL_CODES = 1500  # Total de filas deseadas
ROWS = []

for i in range(TOTAL_CODES):
    base = random.choice(BASE_PROCS)
    code, desc, cat, base_price = base
    state = random.choice(STATES)
    zip_code = str(random.randint(10001, 99950))
    
    # Calcula precios con factor por estado
    state_factor = random.uniform(0.9,1.3)
    avg_price = round(base_price * state_factor, 2)
    low_price = round(avg_price * 0.75, 2)
    high_price = round(avg_price * 1.35, 2)
    
    ROWS.append([code, desc, cat, zip_code, "County", state, low_price, avg_price, high_price, "Estimated"])

# Guardar CSV
with open(FILENAME,"w",newline="",encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["code","description","category","zip_code","county","state","low_price","avg_price","high_price","source"])
    writer.writerows(ROWS)

print(f"✅ {FILENAME} generado con {TOTAL_CODES} códigos de ejemplo")
