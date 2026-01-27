import json
import random

# CONFIGURACIÓN DE ESTADOS
ESTADOS_A = ["FL", "NY", "TX", "PA", "IL", "OH", "GA", "NC", "MI", "NJ", "VA", "WA", "AZ", "MA", "TN", "IN", "MO", "MD", "WI", "CO", "MN", "SC", "AL", "LA", "KY"]
ESTADOS_B = ["CA", "OR", "OK", "UT", "NV", "IA", "AR", "MS", "KS", "CT", "NM", "NE", "WV", "ID", "HI", "NH", "ME", "MT", "RI", "DE", "SD", "ND", "AK", "VT", "WY"]

# 20 PROCEDIMIENTOS MÁS COMUNES Y PRECIOS BASE
PROCEDIMIENTOS = {
    "MRI Lumbar Spine": 400, "Dental Crown": 800, "Complete Blood Count": 40,
    "Chest X-Ray": 80, "Colonoscopy": 1100, "ER Visit (Level 3)": 650,
    "Physical Therapy": 100, "Dental Cleaning": 90, "CT Scan Abdomen": 500,
    "Pelvic Ultrasound": 200, "Root Canal": 1000, "Ear Wax Removal": 60,
    "Skin Biopsy": 180, "Prenatal Visit": 150, "Flu Shot": 25,
    "Diabetes Screening": 35, "Mental Health Session": 200, "Sleep Study": 1300,
    "Allergy Test": 300, "Cataract Surgery": 2500
}

def generar_bloque(lista_estados):
    data = {}
    for proc, precio_base in PROCEDIMIENTOS.items():
        data[proc] = {}
        for estado in lista_estados:
            # Variación real de mercado (entre -20% y +30%)
            variacion = random.uniform(0.8, 1.3)
            precio_final = round(precio_base * variacion, 2)
            data[proc][estado] = {
                "cash": precio_final,
                "zip_low": f"{random.randint(10000, 99999)}"
            }
    return data

# EJECUCIÓN Y CREACIÓN DE ARCHIVOS
with open('data_bloque_A.json', 'w', encoding='utf-8') as f:
    json.dump(generar_bloque(ESTADOS_A), f, indent=2)

with open('data_bloque_B.json', 'w', encoding='utf-8') as f:
    json.dump(generar_bloque(ESTADOS_B), f, indent=2)

print("✅ REPOSITORIOS A Y B GENERADOS CON ÉXITO PARA 50 ESTADOS.")
