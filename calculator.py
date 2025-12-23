import math
from database import get_db_connection

def calculate_system(watts: int, hours: int, no_solar: bool = False):
    """
    Intelligent System Calculator (Q1 2025 Edition - Engineering Corrected).
    """

    # --- 1. PHYSICS & RAW REQUIREMENTS ---
    
    # [CORRECTION] Surge Factor: Inverters fail if they can't handle startup spikes.
    # Defaulting to 1.5x continuous load for safety.
    surge_factor = 1.5
    inverter_required_w = watts * surge_factor
    
    # [CORRECTION] Depth of Discharge (DoD):
    # You cannot drain a battery to 0%. 
    # LiFePO4 safe usage is ~90% (0.9). Lead Acid is ~50% (0.5).
    # Since we default to LiFePO4 in the DB queries, we use 0.9.
    dod_efficiency = 0.9 
    raw_energy_kwh = (watts * hours) / 1000.0
    required_battery_kwh = raw_energy_kwh / dod_efficiency

    # --- 2. VOLTAGE DECISION ---
    # Rule: Keep amps low to reduce heat/cable cost.
    # P = V * I  =>  I = P / V
    if inverter_required_w > 3000 or required_battery_kwh > 5.0:
        system_voltage = 48
    elif inverter_required_w > 1000: 
        system_voltage = 24
    else: 
        system_voltage = 12

    # --- 3. FAST CHARGING CHECK (Yangon "No Solar" Mode) ---
    min_charge_amps = 0
    if no_solar:
        # To charge full battery in 3 hours:
        # Amps = (Required Ah) / 3 Hours
        # Ah = (kWh * 1000) / Voltage
        required_ah = (required_battery_kwh * 1000) / system_voltage
        min_charge_amps = required_ah / 3.0
        
        if min_charge_amps > 60:
            system_voltage = 48
            # Force larger inverter if smaller one lacks charging amps
            if inverter_required_w < 5000:
                inverter_required_w = 5000 

    # --- 4. DATABASE LOOKUP ---
    market_set_found = None

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            
            # STRATEGY A: MARKET PACKAGE
            cur.execute("""
                SELECT name, total_price_mmk, description, inverter_watts, battery_kwh, includes_panels 
                FROM market_packages 
                WHERE inverter_watts >= %s 
                AND battery_kwh >= %s
                AND system_voltage = %s
                ORDER BY total_price_mmk ASC
                LIMIT 1
            """, (inverter_required_w, required_battery_kwh, system_voltage)) 
            
            pkg_row = cur.fetchone()
            # Logic: If user wants no_solar, but package has panels, we skip unless specific flag logic is added.
            # Here we accept the package if it fits specs, assuming panels can be unbundled or user accepts.
            if pkg_row:
                market_set_found = {
                    "name": pkg_row[0],
                    "price": pkg_row[1],
                    "desc": pkg_row[2],
                    "inv_w": pkg_row[3],
                    "bat_kwh": pkg_row[4],
                    "has_panels": pkg_row[5]
                }

            # STRATEGY B: CUSTOM BUILD
            
            # 1. SNAP INVERTER
            cur.execute("""
                SELECT watts, price_mmk, brand, model, max_ac_charge_amps 
                FROM products_inverters 
                WHERE system_voltage = %s 
                AND watts >= %s 
                AND max_ac_charge_amps >= %s
                ORDER BY price_mmk ASC 
                LIMIT 1
            """, (system_voltage, inverter_required_w, min_charge_amps))
            
            inv_row = cur.fetchone()
            
            if inv_row:
                real_inverter = {
                    "watts": inv_row[0],
                    "price": float(inv_row[1]),
                    "name": f"{inv_row[2]} {inv_row[3]}",
                    "charge_amps": inv_row[4]
                }
            else:
                real_inverter = {
                    "watts": inverter_required_w,
                    "price": inverter_required_w * 300, 
                    "name": "Industrial/Parallel Setup",
                    "charge_amps": 100
                }

            # 2. SNAP BATTERY
            # [CORRECTION] Voltage Logic Fix:
            # We strictly check voltage range to avoid 48V Battery on 24V Inverter.
            voltage_upper_bound = system_voltage + 4 # Allow small variance (e.g. 51.2 vs 48)
            
            cur.execute("""
                SELECT price_mmk, kwh, brand, model, volts 
                FROM products_batteries 
                WHERE volts >= %s AND volts < %s
                AND tech_type = 'LiFePO4' 
                ORDER BY price_mmk ASC LIMIT 1
            """, (system_voltage, voltage_upper_bound))
            
            bat_row = cur.fetchone()
            
            if bat_row:
                bat_unit_price = float(bat_row[0])
                bat_unit_kwh = float(bat_row[1])
                bat_name = f"{bat_row[2]} {bat_row[3]} ({bat_row[4]}V)"
                
                # Recalculate quantity based on DoD adjusted requirement
                num_batteries = math.ceil(required_battery_kwh / bat_unit_kwh)
                cost_bat = num_batteries * bat_unit_price
                total_bat_kwh = num_batteries * bat_unit_kwh
            else:
                num_batteries = 1
                cost_bat = required_battery_kwh * 700000
                total_bat_kwh = required_battery_kwh
                bat_name = "Generic LiFePO4 Bank"

            # 3. GET INSTALL COSTS
            cur.execute("SELECT base_labor_mmk, accessory_kit_mmk, mounting_per_panel_mmk, cabinet_cost_mmk FROM ref_installation_costs WHERE voltage_tier = %s", (system_voltage,))
            install_ref = cur.fetchone()
            if not install_ref: install_ref = (100000, 200000, 40000, 0)

    # --- 5. SOLAR CALCULATION ---
    num_panels = 0
    panel_cost = 0
    mounting_cost = 0

    if not no_solar:
        # [CORRECTION] Solar Sizing:
        # Formula: We need to replace the energy used AND fill the battery.
        # But usually, solar runs load + charges battery simultaneously.
        # Required Solar Generation = (Daily Consumption * 1.3 System Losses)
        total_daily_generation_target = raw_energy_kwh * 1.3
        
        # In Yangon, assume 4 Peak Sun Hours (conservative avg)
        required_solar_kw = total_daily_generation_target / 4.0
        
        panel_watts = 590
        panel_price = 300000 
        
        num_panels = math.ceil((required_solar_kw * 1000) / panel_watts)
        panel_cost = num_panels * panel_price
        mounting_cost = num_panels * install_ref[2]

    # --- 6. ASSEMBLE ---
    
    # Calculate Totals
    labor = install_ref[0]
    accessories = install_ref[1]
    cabinet = install_ref[3] if num_batteries > 1 or total_bat_kwh > 10 else 0
    
    total_custom = real_inverter['price'] + cost_bat + panel_cost + mounting_cost + labor + accessories + cabinet

    return {
        "recommendation_type": "CUSTOM_BUILD",
        "system_specs": {
            "inverter": real_inverter['name'],
            "inverter_size_kw": round(real_inverter['watts'] / 1000, 1),
            "system_voltage": system_voltage,
            "battery_model": bat_name,
            "battery_qty": num_batteries,
            "total_storage_kwh": round(total_bat_kwh, 2),
            "solar_panels_count": num_panels
        },
        "estimates": {
            "equipment_cost": int(real_inverter['price'] + cost_bat + cabinet),
            "solar_panels_cost": int(panel_cost),
            "installation_acc": int(labor + accessories + mounting_cost),
            "total_estimated": int(total_custom)
        }
    }