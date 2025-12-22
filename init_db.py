from dotenv import load_dotenv
load_dotenv()

import psycopg2
import os

def init_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set. Cannot initialize.")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    print("Creating Tables...")

    # 1. Inverters
    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_inverters (
        id SERIAL PRIMARY KEY,
        tech_type VARCHAR(50), 
        wattage INT,
        system_voltage INT, 
        price_mmk INT,
        quality_tier VARCHAR(20), 
        date_recorded DATE DEFAULT CURRENT_DATE
    );
    """)

    # 2. Batteries
    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_batteries (
        id SERIAL PRIMARY KEY,
        tech_type VARCHAR(50), 
        voltage FLOAT,
        capacity_ah INT,
        energy_kwh FLOAT, 
        price_mmk INT,
        quality_tier VARCHAR(20),
        date_recorded DATE DEFAULT CURRENT_DATE
    );
    """)

    # 3. Solar Panels
    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_solar_panels (
        id SERIAL PRIMARY KEY,
        brand VARCHAR(50), 
        wattage INT, 
        tech_type VARCHAR(50), 
        price_mmk INT, 
        quality_tier VARCHAR(20),
        date_recorded DATE DEFAULT CURRENT_DATE
    );
    """)

    print("Seeding Initial Data...")
    
    # Clear old data to prevent duplicates on re-run
    cur.execute("TRUNCATE market_inverters, market_batteries, market_solar_panels RESTART IDENTITY;")

    # Seed Inverters
    cur.execute("""
    INSERT INTO market_inverters (tech_type, wattage, system_voltage, price_mmk, quality_tier) VALUES
    ('Off-Grid', 1000, 12, 360000, 'Budget'),
    ('Off-Grid', 3000, 24, 750000, 'Budget'),
    ('Hybrid', 3000, 24, 950000, 'Standard'),
    ('Hybrid', 5000, 48, 1300000, 'Standard'),
    ('Off-Grid', 6000, 48, 1385000, 'Premium'),
    ('Hybrid', 12000, 48, 3300000, 'High-End');
    """)

    # Seed Batteries
    cur.execute("""
    INSERT INTO market_batteries (tech_type, voltage, capacity_ah, energy_kwh, price_mmk, quality_tier) VALUES
    ('LiFePO4', 51.2, 100, 5.12, 3000000, 'Standard'),
    ('LiFePO4', 51.2, 314, 16.07, 6800000, 'Premium'),
    ('Tubular', 12, 200, 2.4, 1850000, 'Standard'),
    ('Tubular', 12, 150, 1.8, 1400000, 'Budget');
    """)

    # Seed Panels
    cur.execute("""
    INSERT INTO market_solar_panels (brand, wattage, tech_type, price_mmk, quality_tier) VALUES
    ('Jinko', 620, 'Bifacial', 310000, 'Tier-1'),
    ('Jinko', 590, 'Monofacial', 300000, 'Tier-1');
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Database Initialized Successfully.")

if __name__ == "__main__":
    init_db()