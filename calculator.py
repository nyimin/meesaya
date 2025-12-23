import math
from database import get_db_connection

def calculate_system(watts: int, hours: int):
    """
    Intelligent System Calculator:
    1. Determines Physics (Voltage, kWh).
    2. CHECKS PROMO SETS FIRST (Real Market Data).
    3. Falls back to Custom Calculation if no set fits.
    """
    
    # 1. Physics & Sizing
    inverter_margin = 1.25
    required_inverter_w = watts * inverter_margin
    required_energy_kwh = (watts * hours) / 1000.0
    
    # Determine Voltage Tier
    if required_inverter_w < 1500: system_voltage = 12
    elif required_inverter_w < 3500: system_voltage = 24
    else: system_voltage = 48

    # 2. Database Intelligence
    market_set_found = None
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            
            # --- STRATEGY A: LOOK FOR A "MARKET SET" ---
            # Find a package where Inverter is strong enough AND Battery is big enough (within 80% tolerance)
            cur.execute("""
                SELECT name, total_price_mmk, description, inverter_watts, battery_kwh, includes_panels 
                FROM market_packages 
                WHERE inverter_watts >= %s 
                AND battery_kwh >= %s
                AND system_voltage = %s
                ORDER BY total_price_mmk ASC
                LIMIT 1
            """, (required_inverter_w, required_energy_kwh * 0.8, system_voltage)) 
            
            row = cur.fetchone()
            if row:
                market_set_found = {
                    "name": row[0],
                    "price": row[1],
                    "desc": row[2],
                    "inv_w": row[3],
                    "bat_kwh": row[4],
                    "has_panels": row[5]
                }

            # --- STRATEGY B: CUSTOM BUILD (Data Gathering) ---
            # Get Install Costs (The "Gap")
            cur.execute("SELECT base_labor_mmk, accessory_kit_mmk, mounting_per_panel_mmk FROM ref_installation_costs WHERE voltage_tier = %s", (system_voltage,))
            install_ref = cur.fetchone()
            if not install_ref: install_ref = (100000, 100000, 40000) # Fallback

            # Get Best Value Inverter
            cur.execute("SELECT AVG(price_mmk) FROM products_inverters WHERE system_voltage = %s AND watts >= %s", (system_voltage, required_inverter_w))
            inv_res = cur.fetchone()
            inv_price = float(inv_res[0]) if inv_res and inv_res[0] else 0

            # Get Lithium Battery Price (Per kWh)
            cur.execute("SELECT AVG(price_mmk / kwh) FROM products_batteries WHERE tech_type = 'LiFePO4' AND volts >= 12")
            bat_res = cur.fetchone()
            bat_price_per_kwh = float(bat_res[0]) if bat_res and bat_res[0] else 600000

    # 3. Decision Logic & Solar Calc
    
    # Target: Charge battery in 4.5 sun hours
    required_solar_kw = (required_energy_kwh / 4.5) * 1.2
    if (required_solar_kw * 1000) < watts: required_solar_kw = watts / 1000 # Minimum to run load
    num_panels = math.ceil((required_solar_kw * 1000) / 550) # Assuming 550W Panels
    panel_cost = num_panels * 300000 # Approx 3 Lakhs per panel
    
    # Calculate Mounting (Rails)
    mounting_cost = num_panels * install_ref[2]

    # --- RESULT: MARKET SET ---
    if market_set_found:
        base_price = market_set_found['price']
        
        # If set doesn't have panels, add them
        addon_cost = 0
        if not market_set_found['has_panels']:
            addon_cost = panel_cost + mounting_cost
        
        total_est = base_price + addon_cost
        
        return {
            "recommendation_type": "MARKET_SET",
            "system_specs": {
                "inverter_size_kw": round(market_set_found['inv_w'] / 1000, 1),
                "system_voltage": system_voltage,
                "battery_storage_kwh": market_set_found['bat_kwh'],
                "recommended_solar_panels": num_panels
            },
            "estimates": {
                "package_name": market_set_found['name'],
                "package_price": int(base_price),
                "solar_addon_cost": int(addon_cost),
                "total_estimated": int(total_est),
                "note": market_set_found['desc']
            }
        }

    # --- RESULT: CUSTOM BUILD ---
    else:
        # Battery Cost (Lithium)
        cost_bat = required_energy_kwh * bat_price_per_kwh
        
        # Install Cost (The "Gap")
        labor = install_ref[0]
        accessories = install_ref[1]
        
        total_custom = inv_price + cost_bat + panel_cost + mounting_cost + labor + accessories
        
        return {
            "recommendation_type": "CUSTOM_BUILD",
            "system_specs": {
                "inverter_size_kw": round(required_inverter_w / 1000, 1),
                "system_voltage": system_voltage,
                "battery_storage_kwh": round(required_energy_kwh, 2),
                "recommended_solar_panels": num_panels
            },
            "estimates": {
                "equipment_cost": int(inv_price + cost_bat),
                "solar_panels_cost": int(panel_cost),
                "installation_and_accessories": int(labor + accessories + mounting_cost),
                "total_estimated": int(total_custom)
            }
        }