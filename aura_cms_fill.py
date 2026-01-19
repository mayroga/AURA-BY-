import sqlite3
import pandas as pd
import requests

def ingest_real_market_data():
    """
    Descarga datos oficiales de CMS para cubrir los 50 estados.
    Enfocado en Physician Fee Schedule (Lo que cobran los médicos).
    """
    print("🌐 Conectando con los servidores de datos de salud de USA...")
    
    # URL de datos abiertos de CMS (Physician Fee Schedule)
    # Nota: En producción, se pueden añadir más datasets específicos.
    cms_url = "https://data.cms.gov/resource/7b3x-3k6u.csv?$limit=5000"
    
    try:
        df = pd.read_csv(cms_url)
        print(f"📊 {len(df)} registros descargados. Iniciando normalización para AURA...")

        # Mapeo de columnas CMS a estructura AURA
        # Intentamos localizar columnas de pago y ubicación
        # Nota: Los nombres de columnas en CMS pueden variar según el año
        df.columns = [c.lower() for c in df.columns]
        
        # Filtramos y renombramos para que MAIN.PY lo entienda
        # Buscamos columnas como 'hcpcs_code', 'non_fac_pmt_amt' (Pago en clínica)
        aura_data = pd.DataFrame()
        aura_data['description'] = df['hcpcs_description'] if 'hcpcs_description' in df.columns else "Procedimiento Médico"
        aura_data['cpt_code'] = df['hcpcs_code']
        aura_data['low_price'] = df['non_fac_pmt_amt'] if 'non_fac_pmt_amt' in df.columns else 0
        aura_data['high_price'] = aura_data['low_price'] * 1.5 # Estimado educativo premium
        aura_data['state'] = df['state'] if 'state' in df.columns else "USA"
        aura_data['zip_code'] = "00000" # CMS suele dar por estado/localidad, no siempre ZIP exacto
        aura_data['provider_type'] = "Medical Doctor"
        aura_data['source_file'] = "CMS Official Data"

        # Limpieza: eliminar filas sin precio
        aura_data = aura_data[aura_data['low_price'] > 0]

        # Inyectar en la base de datos que lee MAIN.PY
        conn = sqlite3.connect('aura_brain.db')
        aura_data.to_sql('prices', conn, if_exists='append', index=False)
        conn.close()

        print(f"✅ ÉXITO: {len(aura_data)} registros oficiales de salud inyectados en Aura.")
        print("💡 Ahora AURA puede comparar precios reales del mercado contra opciones locales.")

    except Exception as e:
        print(f"❌ Error al conectar con datos oficiales: {e}")

if __name__ == "__main__":
    ingest_real_market_data()
