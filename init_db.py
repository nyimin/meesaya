import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def init_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set.")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    print("🔄 Resetting Database Schema...")
    
    # 0. CHAT HISTORY
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50),
            role VARCHAR(10),
            message_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 1. INDIVIDUAL COMPONENTS (For Custom Calculations)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products_inverters (
            id SERIAL PRIMARY KEY,
            brand VARCHAR(50), model VARCHAR(50), 
            type VARCHAR(20), watts INT, system_voltage INT, 
            price_mmk INT, tier VARCHAR(20)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products_batteries (
            id SERIAL PRIMARY KEY,
            brand VARCHAR(50), tech_type VARCHAR(20), 
            volts FLOAT, amp_hours INT, kwh FLOAT, 
            price_mmk INT, tier VARCHAR(20)
        );
    """)

    # 2. INSTALLATION REFERENCE (The "Gap" Logic)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ref_installation_costs (
            voltage_tier INT PRIMARY KEY,
            base_labor_mmk INT,      -- Team Labor
            accessory_kit_mmk INT,   -- Breakers, Box, Cables, ATS
            mounting_per_panel_mmk INT
        );
    """)

    # 3. MARKET PACKAGES (The "Shop Sets")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_packages (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),              -- e.g. "5kW Family Starter Set"
            inverter_watts INT,
            battery_kwh FLOAT,
            system_voltage INT,
            total_price_mmk INT,            -- The Promo Price
            includes_panels BOOLEAN,
            description TEXT
        );
    """)

    # Clear old data
    cur.execute("TRUNCATE products_inverters, products_batteries, ref_installation_costs, market_packages RESTART IDENTITY;")

    print("📥 Seeding Real Market Data (Jan 2025)...")

    # --- SEED INVERTERS ---
    cur.executemany("""
        INSERT INTO products_inverters (brand, model, type, watts, system_voltage, price_mmk, tier) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, [
        ('Must', 'PV1800', 'Off-Grid', 1000, 12, 360000, 'Budget'),
        ('Solar Nest', 'V2', 'Hybrid', 3000, 24, 950000, 'Standard'),
        ('Felicity', 'IVEM', 'Hybrid', 5000, 48, 1300000, 'Standard'),
        ('Growatt', 'SPF-6000', 'Off-Grid', 6000, 48, 1385000, 'Premium'),
        ('Deye', 'SUN-5K', 'Hybrid', 5000, 48, 2200000, 'Premium')
    ])

    # --- SEED BATTERIES ---
    cur.executemany("""
        INSERT INTO products_batteries (brand, tech_type, volts, amp_hours, kwh, price_mmk, tier) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, [
        ('Local', 'LeadAcid', 12, 100, 1.2, 300000, 'Budget'),
        ('Must', 'LiFePO4', 12.8, 100, 1.28, 850000, 'Standard'),
        ('Felicity', 'LiFePO4', 25.6, 100, 2.56, 1600000, 'Standard'),
        ('Felicity', 'LiFePO4', 51.2, 100, 5.12, 3000000, 'Standard'),
        ('Lvtopsun', 'LiFePO4', 51.2, 314, 16.0, 6800000, 'Premium')
    ])

    # --- SEED INSTALLATION COSTS (The Validated "Gap") ---
    cur.executemany("""
        INSERT INTO ref_installation_costs (voltage_tier, base_labor_mmk, accessory_kit_mmk, mounting_per_panel_mmk) VALUES (%s, %s, %s, %s)
    """, [
        (12, 50000, 150000, 40000),   # 12V: DIY friendly, cheap parts
        (24, 150000, 350000, 45000),  # 24V: Standard install
        (48, 300000, 700000, 50000)   # 48V: Pro team, heavy cables, ATS
    ])

    # --- SEED MARKET SETS (The "Promo Packages") ---
    # These match the observed 2024/2025 FB Ads
    cur.executemany("""
        INSERT INTO market_packages (name, inverter_watts, battery_kwh, system_voltage, total_price_mmk, includes_panels, description) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, [
        ('Budget 1kW Starter Set', 1000, 1.2, 12, 850000, False, 'Perfect for TV, Lights, and Wifi. Includes 100Ah Battery + Inverter.'),
        ('Family Standard 3kW Set', 3000, 2.5, 24, 3200000, False, 'Runs Rice Cooker + Fridge. Includes 3kW Hybrid + 2.5kWh Lithium.'),
        ('Felicity 5kW Promo Set', 5000, 5.1, 48, 5200000, False, 'Best Seller. Runs 1 Aircon + Fridge. Includes Felicity 5kW + 5kWh Lithium + Basic Install.'),
        ('Deye Premium 6kW System', 6000, 10.2, 48, 10500000, False, 'Whole Home Backup. Deye 6kW + 2x Lithium Batteries + Premium Cabinet.')
    ])

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database Initialized with Smart Sets & Real Prices.")

if __name__ == "__main__":
    init_db()