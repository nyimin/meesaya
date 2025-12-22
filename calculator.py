from database import get_db_connection

def calculate_system(watts: int, hours: int):
    """
    Calculates system requirements and estimates costs based on database prices.
    """
    # 1. Physics & Sizing
    inverter_margin = 1.25
    required_inverter_w = watts * inverter_margin
    
    # Determine Voltage
    if required_inverter_w < 1500:
        system_voltage = 12
    elif required_inverter_w < 3500:
        system_voltage = 24
    else:
        system_voltage = 48

    # Energy Requirements
    required_energy_kwh = (watts * hours) / 1000.0

    # 2. Database Queries
    conn = get_db_connection()
    cur = conn.cursor()

    # Get Inverter Price Estimate
    # Find average price of inverters that fit the voltage and are strong enough
    cur.execute("""
        SELECT AVG(price_mmk) FROM market_inverters 
        WHERE system_voltage = %s AND wattage >= %s AND wattage <= %s
    """, (system_voltage, required_inverter_w, required_inverter_w + 3000))
    
    avg_inv_price = cur.fetchone()[0]
    
    # Fallback if specific range not found, just get minimum viable
    if not avg_inv_price:
        cur.execute("SELECT MIN(price_mmk) FROM market_inverters WHERE wattage >= %s", (required_inverter_w,))
        avg_inv_price = cur.fetchone()[0]
    
    inv_price = float(avg_inv_price) if avg_inv_price else 0

    # Get Battery Price Estimates (Per kWh)
    # Lithium
    cur.execute("SELECT AVG(price_mmk / energy_kwh) FROM market_batteries WHERE tech_type = 'LiFePO4'")
    li_price_per_kwh = cur.fetchone()[0] or 450000 # Fallback default
    
    # Lead Acid / Tubular
    cur.execute("SELECT AVG(price_mmk / energy_kwh) FROM market_batteries WHERE tech_type = 'Tubular'")
    la_price_per_kwh = cur.fetchone()[0] or 250000 # Fallback default

    conn.close()

    # 3. Cost Calculation
    # Lithium Calculation (Assuming 90% DoD efficiency)
    needed_kwh_li = required_energy_kwh / 0.9
    cost_bat_li = needed_kwh_li * float(li_price_per_kwh)

    # Lead Acid Calculation (Assuming 50% DoD efficiency - they need to be 2x bigger)
    needed_kwh_la = required_energy_kwh / 0.5
    cost_bat_la = needed_kwh_la * float(la_price_per_kwh)

    # Overhead (Cables, Breakers, Install) ~ 15% of equipment
    overhead_li = (inv_price + cost_bat_li) * 0.15
    overhead_la = (inv_price + cost_bat_la) * 0.15

    return {
        "system_specs": {
            "inverter_size_kw": round(required_inverter_w / 1000, 1),
            "system_voltage": system_voltage,
            "required_backup_kwh": round(required_energy_kwh, 2)
        },
        "estimates": {
            "inverter_approx_price": int(inv_price),
            "lithium_option": {
                "battery_cost": int(cost_bat_li),
                "total_estimated": int(inv_price + cost_bat_li + overhead_li),
                "lifespan": "8-10 Years"
            },
            "tubular_option": {
                "battery_cost": int(cost_bat_la),
                "total_estimated": int(inv_price + cost_bat_la + overhead_la),
                "lifespan": "2-3 Years"
            },
            "installation_overhead_approx": int(overhead_li)
        }
    }