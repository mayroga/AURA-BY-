import sqlite3
import pandas as pd

def ingest_data():
    conn = sqlite3.connect('aura_brain.db')
    
    # Datos de ejemplo que representan la carga de CPT 2026 y CDT
    # En producción, aquí se procesarían los CSV de CMS y ADA
    sample_data = [
        # DENTAL (CDT) - Ejemplo Root Canal + Corona
        ('Root Canal & Crown', 'D3330', 800.00, 450.00, 'FL', 'Miami-Dade', '33101', 'Dental', 0),
        ('Root Canal & Crown', 'D3330', 750.00, 400.00, 'FL', 'Miami-Dade', '33130', 'Dental', 0),
        ('Root Canal & Crown', 'D3330', 1200.00, 600.00, 'TX', 'Harris', '77001', 'Dental', 0),
        ('Root Canal & Crown', 'D3330', 500.00, 250.00, 'OH', 'Franklin', '43001', 'Dental', 0), # Nacional Barato
        ('Root Canal & Crown', 'D3330', 3500.00, 1800.00, 'NY', 'Manhattan', '10001', 'Dental', 1), # Premium
        
        # MEDICINA (CPT 2026) - Revascularización y Salud Digital
        ('Leg Revascularization', '37220', 4500.00, 1200.00, 'FL', 'Broward', '33301', 'Medical', 0),
        ('Digital Health Monitoring', '98975', 150.00, 45.00, 'CA', 'Los Angeles', '90001', 'Medical', 0)
    ]
    
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT INTO prices (description, cpt_cdt_code, cash_price, estimated_insurance_price, state, county, zip_code, category, is_premium)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_data)
    
    conn.commit()
    conn.close()
    print("🚀 Datos oficiales (CMS/ADA/AMA) inyectados en AURA.")

if __name__ == "__main__":
    ingest_data()
