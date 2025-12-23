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

    print("🔄 Resetting Database Schema (DROP & RECREATE)...")

    # --- 0. CLEANUP (DROP OLD TABLES) ---
    # We must drop tables to ensure new columns (like max_ac_charge_amps) are created.
    tables_to_drop = [
        "products_inverters", 
        "products_batteries", 
        "products_solar_panels", 
        "products_commercial_bess", 
        "products_portables", 
        "vendors", 
        "ref_installation_costs", 
        "market_packages",
        "chat_history" # Optional: Comment out if you want to keep chat logs
    ]
    
    for t in tables_to_drop:
        cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE;")

    # --- 1. CORE PRODUCT TABLES ---
    
    # 1.0 Chat History
    cur.execute("""
        CREATE TABLE chat_history (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50),
            role VARCHAR(10),
            message_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 1.1 Inverters
    cur.execute("""
        CREATE TABLE products_inverters (
            id SERIAL PRIMARY KEY,
            brand VARCHAR(50), model VARCHAR(100), 
            type VARCHAR(50), watts INT, system_voltage INT, 
            max_ac_charge_amps INT, 
            price_mmk INT, tier VARCHAR(20),
            notes TEXT
        );
    """)

    # 1.2 Batteries
    cur.execute("""
        CREATE TABLE products_batteries (
            id SERIAL PRIMARY KEY,
            brand VARCHAR(50), model VARCHAR(100), tech_type VARCHAR(20), 
            volts FLOAT, amp_hours INT, kwh FLOAT, 
            warranty_years INT, cell_grade VARCHAR(50),
            price_mmk INT, tier VARCHAR(20),
            notes TEXT
        );
    """)

    # 1.3 Solar Panels
    cur.execute("""
        CREATE TABLE products_solar_panels (
            id SERIAL PRIMARY KEY,
            brand VARCHAR(50), model VARCHAR(50), watts INT,
            type VARCHAR(50), price_mmk INT, warranty_years INT
        );
    """)

    # --- 2. NEW: COMMERCIAL & PORTABLE ---
    cur.execute("""
        CREATE TABLE products_commercial_bess (
            id SERIAL PRIMARY KEY,
            brand VARCHAR(50), model VARCHAR(100),
            kwh FLOAT, voltage_type VARCHAR(20), 
            price_mmk INT, description TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE products_portables (
            id SERIAL PRIMARY KEY,
            brand VARCHAR(50), model VARCHAR(50),
            watts INT, kwh FLOAT, price_mmk INT,
            description TEXT
        );
    """)

    # --- 3. NEW: VENDOR INTELLIGENCE ---
    cur.execute("""
        CREATE TABLE vendors (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            category VARCHAR(50), 
            specialty TEXT,
            known_brands TEXT
        );
    """)

    # --- 4. INSTALLATION & PACKAGES ---
    cur.execute("""
        CREATE TABLE ref_installation_costs (
            voltage_tier INT PRIMARY KEY,
            base_labor_mmk INT,      
            accessory_kit_mmk INT,   
            mounting_per_panel_mmk INT,
            cabinet_cost_mmk INT
        );
    """)

    cur.execute("""
        CREATE TABLE market_packages (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),              
            inverter_watts INT,
            battery_kwh FLOAT,
            system_voltage INT,
            total_price_mmk INT,            
            includes_panels BOOLEAN,
            description TEXT
        );
    """)

    print("📥 Seeding Comprehensive Market Survey Data (Q1 2025)...")

    # ==========================================
    # 1. INVERTERS (Detailed from Report)
    # ==========================================
    cur.executemany("""
        INSERT INTO products_inverters (brand, model, type, watts, system_voltage, max_ac_charge_amps, price_mmk, tier, notes) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, [
        # 12V Budget
        ('Must', 'PV1800 Budget', 'Off-Grid', 1000, 12, 20, 360000, 'Budget', 'Entry level'),
        ('Comfos', 'CF-1500', 'Off-Grid', 1500, 12, 30, 0, 'Budget', 'Vietnam made, usually bundled'),
        ('Shark Topsun', '12V Off-Grid', 'Off-Grid', 1500, 12, 30, 750000, 'Budget', 'Known for durability in budget class'),
        
        # 24V Mid-Range
        ('Dragon Power', '24V Standard', 'Off-Grid', 3500, 24, 60, 670000, 'Budget', 'Budget mid-range option'),
        ('Shark Topsun', '24V Off-Grid', 'Off-Grid', 3500, 24, 60, 950000, 'Standard', 'Solid 24V performer'),
        ('Felicity', 'IVEM3024', 'Hybrid', 3000, 24, 60, 950000, 'Standard', 'Reliable Hybrid'),

        # 48V The "Standard"
        ('Felicity', 'IVEM5048', 'Hybrid', 5000, 48, 80, 1300000, 'Standard', 'Entry 48V Hybrid'),
        ('Growatt', 'SPF 6000 ES Plus', 'Off-Grid', 6000, 48, 100, 1385000, 'Premium', 'Market Leader. High surge capacity.'),
        ('Shark Topsun', '48V Off-Grid', 'Off-Grid', 6500, 48, 100, 1490000, 'Standard', 'High power budget alternative'),
        ('Deye', 'SUN-6K-SG03', 'Hybrid', 6000, 48, 120, 2400000, 'Premium', 'Top tier, often sold in bundles'),

        # High Power Residential
        ('Shark Topsun', '11kW High Power', 'Off-Grid', 11000, 48, 150, 3100000, 'High Power', 'For large homes/shops'),
        ('Shark Topsun', '12kW High Power', 'Off-Grid', 12000, 48, 150, 4900000, 'High Power', 'Max residential power')
    ])

    # ==========================================
    # 2. BATTERIES (The "War of Warranties")
    # ==========================================
    cur.executemany("""
        INSERT INTO products_batteries (brand, model, tech_type, volts, amp_hours, kwh, warranty_years, cell_grade, price_mmk, tier, notes) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, [
        # 12V/24V Segment
        ('Shark Topsun', '12V 100Ah', 'LiFePO4', 12.8, 100, 1.28, 3, 'Standard', 880000, 'Budget', 'Replace Lead Acid'),
        ('Shark Topsun', '12V 200Ah', 'LiFePO4', 12.8, 200, 2.56, 3, 'Standard', 1600000, 'Budget', 'Large 12V capacity'),
        ('Felicity', '24V 200Ah', 'LiFePO4', 25.6, 200, 5.12, 5, 'Grade A', 2800000, 'Standard', 'Good for 24V Aircon systems'),

        # 48V (51.2V) Segment - The Main Battleground
        ('Felicity', 'FLA 100Ah', 'LiFePO4', 51.2, 100, 5.12, 7, 'Grade A', 3000000, 'Standard', '7 Year Warranty entry'),
        ('Deye', 'RW-L5.1', 'LiFePO4', 51.2, 100, 5.12, 10, 'Grade A', 3750000, 'Premium', 'Premium compact, 10Y Warranty'),
        
        ('Shark Topsun', 'V1 200Ah', 'LiFePO4', 51.2, 200, 10.24, 5, 'Standard', 4900000, 'Budget', 'Cheapest 10kWh option'),
        ('Lvtopsun', 'G3 200Ah', 'LiFePO4', 51.2, 200, 10.24, 5, 'Grade A', 5100000, 'Standard', 'Reliable workhorse'),
        
        # The 300Ah+ Heavyweights
        ('Felicity', 'LPBF 300Ah', 'LiFePO4', 51.2, 300, 15.36, 5, 'Grade A', 5150000, 'Standard', 'Good price per kWh'),
        ('Lvtopsun', 'G3 300Ah', 'LiFePO4', 51.2, 300, 15.36, 5, 'Grade A', 5700000, 'Standard', 'Older generation, still good'),
        ('Lvtopsun', 'G4 314Ah', 'LiFePO4', 51.2, 314, 16.0, 10, 'EVE Grade A', 6800000, 'Premium', 'Market Best Seller. 10Y Warranty.'),
        ('Bicodi', '314Ah', 'LiFePO4', 51.2, 314, 16.0, 10, 'Grade A', 7300000, 'Premium', 'High end competitor'),
        ('Deye', 'SE-G5.3 (Stack)', 'LiFePO4', 51.2, 314, 16.0, 10, 'Grade A', 7250000, 'Premium', 'Deye Ecosystem Native'),
        ('CATL', '320Ah', 'LiFePO4', 51.2, 320, 16.3, 5, 'CATL', 6500000, 'Standard', 'Raw capacity focus')
    ])

    # ==========================================
    # 3. SOLAR PANELS
    # ==========================================
    cur.executemany("""
        INSERT INTO products_solar_panels (brand, model, watts, type, price_mmk, warranty_years)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, [
        ('Jinko', 'Tiger Neo N-Type', 590, 'Monofacial', 290000, 30),
        ('Jinko', 'Tiger Neo N-Type', 620, 'Bifacial', 310000, 30),
        ('Longi', 'Hi-MO 6', 580, 'Monofacial', 285000, 25)
    ])

    # ==========================================
    # 4. VENDORS (The "Who to Call")
    # ==========================================
    cur.executemany("""
        INSERT INTO vendors (name, category, specialty, known_brands)
        VALUES (%s, %s, %s, %s)
    """, [
        ('Yoon Electronic', 'Aggregator', 'Cash & Carry, Huge Inventory, Price Lists', 'Felicity, Lvtopsun, Deye, Dapa, Bicodi'),
        ('MZO Electrical', 'Aggregator', 'Package Deals, Inverter+Battery Bundles', 'Shark Topsun, Growatt, SVC'),
        ('Power Light', 'Aggregator', 'Aggressive Pricing, Hardware Subsidies', 'Growatt, Budget Batteries'),
        ('Ray Electric (North Dagon)', 'Aggregator', 'Budget Systems, 12V/24V Focus', 'Shark Topsun, 12V Systems'),
        ('Aether Solar Engineering', 'Engineering', 'Technical Education, Grade A Verification', 'Jinko, Solis, Omega, EVE Cells'),
        ('Alpha Engineering', 'Engineering', 'Custom Residential, Technical Correctness', 'Solis, Tri-G'),
        ('Hla Min Htet', 'Engineering', 'Commercial Projects, Large Scale', 'BESS, High Voltage'),
        ('Deye Solar Myanmar (GAES)', 'Brand Distributor', 'Official Deye Support', 'Deye Ecosystem'),
        ('Dyness Myanmar (MWL)', 'Brand Distributor', 'High Voltage Battery Stacks', 'Dyness HV'),
        ('Power Station Myanmar', 'Specialist', 'Apartment Cabinets, Portables', 'EcoFlow, Growatt All-in-One')
    ])

    # ==========================================
    # 5. COMMERCIAL & PORTABLES
    # ==========================================
    cur.executemany("""
        INSERT INTO products_commercial_bess (brand, model, kwh, voltage_type, price_mmk, description)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, [
        ('Dyness', 'Stack 100 (Small)', 40.96, 'High Voltage', 31400000, 'HV Stack for small factory/office.'),
        ('Dyness', 'Stack 100 (Large)', 61.44, 'High Voltage', 45400000, 'HV Stack for medium industrial load.'),
        ('Growatt', 'WIT Commercial', 100.0, 'High Voltage', 80000000, 'Inverter + Battery Containerized solution estimate.')
    ])

    cur.executemany("""
        INSERT INTO products_portables (brand, model, watts, kwh, price_mmk, description)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, [
        ('EcoFlow', 'River 2', 300, 0.25, 770000, 'Portable, for laptop/wifi only.'),
        ('EcoFlow', 'Delta 2', 1800, 1.0, 2550000, 'Can run small appliances, coffee maker.'),
        ('EcoFlow', 'Delta Pro', 3600, 3.6, 6600000, 'Heavy duty portable, can run small AC briefly.')
    ])

    # ==========================================
    # 6. MARKET PACKAGES (From Report Analysis)
    # ==========================================
    cur.executemany("""
        INSERT INTO market_packages (name, inverter_watts, battery_kwh, system_voltage, total_price_mmk, includes_panels, description) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, [
        ('Entry 12V Lighting Set', 1500, 1.28, 12, 1500000, False, 'Shark Topsun 1.5kW + 100Ah Lithium. For Wifi/Lights only.'),
        ('Mid-Range 24V Fridge Set', 3500, 2.56, 24, 3600000, False, '3.5kW Inverter + 24V 100Ah. Runs Fridge + Lights. No Aircon.'),
        ('Standard 6kW Home (Bundled)', 6000, 15.3, 48, 7400000, False, 'Growatt 6kW + Felicity/Lvtopsun 300Ah. Runs 1HP Aircon. Best Value.'),
        ('Premium Deye Ecosystem', 6000, 16.0, 48, 10500000, False, 'Deye 6kW + Deye 314Ah (10Y Warranty). Smart ecosystem, full app control.'),
        ('Yangon Condo All-in-One', 5000, 5.0, 48, 6200000, False, 'Growatt Cabinet style. 5kWh. fits in living room.'),
        ('Full Off-Grid Mansion', 12000, 32.0, 48, 160000000, True, 'Shark Topsun 12kW + 2x 314Ah Batteries + 12 Jinko Panels.')
    ])

    # --- INSTALL COSTS ---
    cur.executemany("""
        INSERT INTO ref_installation_costs (voltage_tier, base_labor_mmk, accessory_kit_mmk, mounting_per_panel_mmk, cabinet_cost_mmk) 
        VALUES (%s, %s, %s, %s, %s)
    """, [
        (12, 50000, 250000, 40000, 0),
        (24, 150000, 450000, 45000, 100000), 
        (48, 300000, 700000, 50000, 250000) 
    ])

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database Fully Hydrated with Comprehensive Survey Data.")

if __name__ == "__main__":
    init_db()