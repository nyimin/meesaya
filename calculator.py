import math
from database import get_db_connection

def calculate_system(watts: int, hours: int, no_solar: bool = False):
    """
    Intelligent System Calculator (Q1 2025 Edition).
    
    Features:
    1. Voltage Logic: Standardizes on 48V for Aircons/Fast Charging.
    2. Yangon Mode: Checks 'max_ac_charge_amps' if no_solar is True.
    3. Snap-to-Market: Finds real, buyable components (e.g., 5kW for 4kW load).
    4. Unpredictable Grid: Oversizes solar to charge in 4 hours.
    """
    
    # --- 1. PHYSICS & RAW REQUIREMENTS ---
    inverter_margin = 1.25
    raw_required_w = watts * inverter_margin
    required_energy_kwh = (watts * hours) / 1000.0
    
    # --- 2. VOLTAGE DECISION ---
    # Rule 1: High Load (>2000W) or Aircons -> 48V
    # Rule 2: High Energy (>5kWh) without solar -> 48V (needs fast charging)
    if watts > 2000 or (no_solar and required_energy_kwh > 5.0):
        system_voltage = 48
    elif raw_required_w < 1500: 
        system_voltage = 12
    elif raw_required_w < 3500: 
        system_voltage = 24
    else: 
        system_voltage = 48

    # --- 3. FAST CHARGING CHECK (Yangon "No Solar" Mode) ---
    # We must ensure the inverter has a large enough charger (AC to DC)
    # Target: Charge battery in ~3 hours of grid availability.
    min_charge_amps = 0
    if no_solar:
        # Amps = (Wh * Efficiency) / Voltage / 3 Hours
        min_charge_amps = (required_energy_kwh * 1000 * 1.15) / system_voltage / 3.0
        
        # If massive amps needed (>60A), force 48V and at least 5kW inverter capacity
        # (Small inverters usually don't have >60A chargers)
        if min_charge_amps > 60:
            system_voltage = 48
            if raw_required_w < 5000:
                raw_required_w = 5000 

    # --- 4. DATABASE LOOKUP: STRATEGY A (MARKET PACKAGE) ---
    market_set_found = None
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            
            # Find a pre-bundled package that meets specs
            # We prefer packages that match the 'no_solar' preference
            cur.execute("""
                SELECT name, total_price_mmk, description, inverter_watts, battery_kwh, includes_panels 
                FROM market_packages 
                WHERE inverter_watts >= %s 
                AND battery_kwh >= %s
                AND system_voltage = %s
                AND includes_panels = %s
                ORDER BY total_price_mmk ASC
                LIMIT 1
            """, (raw_required_w, required_energy_kwh * 0.9, system_voltage, not no_solar)) 
            
            pkg_row = cur.fetchone()
            if pkg_row:
                market_set_found = {
                    "name": pkg_row[0],
                    "price": pkg_row[1],
                    "desc": pkg_row[2],
                    "inv_w": pkg_row[3],
                    "bat_kwh": pkg_row[4],
                    "has_panels": pkg_row[5]
                }

            # --- STRATEGY B: CUSTOM BUILD (COMPONENT SNAP) ---
            
            # 1. SNAP INVERTER (Find smallest REAL inverter >= requirement)
            # We also check max_ac_charge_amps if needed
            cur.execute("""
                SELECT watts, price_mmk, brand, model, max_ac_charge_amps 
                FROM products_inverters 
                WHERE system_voltage = %s 
                AND watts >= %s 
                AND max_ac_charge_amps >= %s
                ORDER BY price_mmk ASC 
                LIMIT 1
            """, (system_voltage, raw_required_w, min_charge_amps))
            
            inv_row = cur.fetchone()
            
            if inv_row:
                real_inverter = {
                    "watts": inv_row[0],
                    "price": float(inv_row[1]),
                    "name": f"{inv_row[2]} {inv_row[3]}",
                    "charge_amps": inv_row[4]
                }
            else:
                # Fallback: Load is too high for our DB (e.g. >12kW) or no specific match
                # Create a "Virtual" Industrial estimation
                real_inverter = {
                    "watts": raw_required_w,
                    "price": raw_required_w * 250, # Estimate ~250k per kW for large industrial
                    "name": "Custom Industrial/Parallel Inverter Setup",
                    "charge_amps": 999
                }

            # 2. SNAP BATTERY (Find real battery blocks)
            # Logic: If 48V and huge capacity, look for 314Ah blocks (High Density)
            if system_voltage == 48 and required_energy_kwh > 10:
                 # Look for Amp Hours >= 280
                cur.execute("""
                    SELECT price_mmk, kwh, brand, model 
                    FROM products_batteries 
                    WHERE volts > 40 AND amp_hours >= 280 
                    ORDER BY price_mmk ASC LIMIT 1
                """)
            else:
                # Look for standard batteries matching voltage
                cur.execute("""
                    SELECT price_mmk, kwh, brand, model 
                    FROM products_batteries 
                    WHERE volts >= %s AND tech_type = 'LiFePO4' 
                    ORDER BY price_mmk ASC LIMIT 1
                """, (system_voltage,))
            
            bat_row = cur.fetchone()
            
            if bat_row:
                bat_unit_price = float(bat_row[0])
                bat_unit_kwh = float(bat_row[1])
                bat_name = f"{bat_row[2]} {bat_row[3]}"
                
                # Calculate quantity needed
                num_batteries = math.ceil(required_energy_kwh / bat_unit_kwh)
                cost_bat = num_batteries * bat_unit_price
                total_bat_kwh = num_batteries * bat_unit_kwh
            else:
                # Fallback estimate
                num_batteries = 1
                cost_bat = required_energy_kwh * 600000
                total_bat_kwh = required_energy_kwh
                bat_name = "Generic LiFePO4 Bank"

            # 3. GET INSTALL COSTS
            cur.execute("""
                SELECT base_labor_mmk, accessory_kit_mmk, mounting_per_panel_mmk, cabinet_cost_mmk 
                FROM ref_installation_costs 
                WHERE voltage_tier = %s
            """, (system_voltage,))
            install_ref = cur.fetchone()
            if not install_ref: install_ref = (100000, 200000, 40000, 0) # Safety default

    # --- 5. SOLAR CALCULATION (Unpredictable Grid) ---
    num_panels = 0
    panel_cost = 0
    mounting_cost = 0
    panel_name = "None"
    
    if not no_solar:
        # Rapid Recovery Formula:
        # We assume grid is bad. Must charge battery + run load in ~4 hours of sun.
        total_daily_need_kwh = required_energy_kwh + (watts * 4 / 1000.0)
        
        # 1.3 factor for heat/dust loss
        required_solar_kw = (total_daily_need_kwh / 4.0) * 1.3
        
        # Standardize on 590W Jinko (common in DB)
        panel_watts = 590
        panel_price = 300000 # Approx from DB
        
        num_panels = math.ceil((required_solar_kw * 1000) / panel_watts)
        panel_cost = num_panels * panel_price
        mounting_cost = num_panels * install_ref[2]
        panel_name = f"{num_panels}x {panel_watts}W Jinko (or similar)"

    # --- 6. ASSEMBLE RETURN DATA ---

    # Option A: Market Package (Best Value/Simplicity)
    if market_set_found:
        return {
            "recommendation_type": "MARKET_SET",
            "system_specs": {
                "inverter_size_kw": round(market_set_found['inv_w'] / 1000, 1),
                "system_voltage": system_voltage,
                "battery_storage_kwh": round(market_set_found['bat_kwh'], 1),
                "recommended_solar_panels": 0 # Package defines this
            },
            "estimates": {
                "package_name": market_set_found['name'],
                "total_estimated": int(market_set_found['price']),
                "note": f"Matched a verified promo package: {market_set_found['desc']}"
            }
        }

    # Option B: Custom Build (Snapped Components)
    else:
        # Costs
        labor = install_ref[0]
        accessories = install_ref[1]
        cabinet = install_ref[3] if num_batteries > 1 or total_bat_kwh > 10 else 0
        
        total_custom = real_inverter['price'] + cost_bat + panel_cost + mounting_cost + labor + accessories + cabinet
        
        # Construct Notes
        inv_note = f"Standard market size ({real_inverter['name']})"
        if real_inverter['watts'] > raw_required_w * 1.2:
            inv_note += " (upsized for availability)"
        
        bat_note = f"{num_batteries}x {bat_name}"
        
        charge_note = ""
        if no_solar and min_charge_amps > 30:
            charge_note = f" Optimized for fast grid charging ({real_inverter.get('charge_amps', '?')}A)."

        return {
            "recommendation_type": "CUSTOM_BUILD",
            "system_specs": {
                "inverter_size_kw": round(real_inverter['watts'] / 1000, 1),
                "system_voltage": system_voltage,
                "battery_storage_kwh": round(total_bat_kwh, 2),
                "recommended_solar_panels": num_panels
            },
            "estimates": {
                "equipment_cost": int(real_inverter['price'] + cost_bat + cabinet),
                "solar_panels_cost": int(panel_cost),
                "installation_and_accessories": int(labor + accessories + mounting_cost),
                "total_estimated": int(total_custom),
                "note": f"Build: {inv_note} + {bat_note}.{charge_note}"
            }
        }