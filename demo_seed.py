"""
demo_seed.py — 1-Click Clean Slate Database & Memory Reset for Live Demos
Resets PostgreSQL tables (inventory, suppliers, purchase_orders, audit_log,
manager_notifications, copilot_insights) and resets the FastAPI in-memory
Autonomous Guardrail state so every live presentation starts from a predictable state.
"""
import os
import json
import urllib.request
import psycopg2

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "fmcg_procurement"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "1234"),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432")
}


def reset_database():
    print("🔄 Connecting to PostgreSQL ('fmcg_procurement')...")
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            # 1. Force drop old tables to ensure a true clean slate
            cur.execute("""
                DROP TABLE IF EXISTS 
                    inventory, suppliers, purchase_orders, audit_log, 
                    manager_notifications, copilot_insights CASCADE;
            """)

            # 2. Recreate tables with the exact required schema
            cur.execute("""
                CREATE TABLE inventory (
                    item_id SERIAL PRIMARY KEY,
                    material_name VARCHAR(100) UNIQUE NOT NULL,
                    current_stock_tons NUMERIC(10, 2) NOT NULL,
                    safety_stock_tons NUMERIC(10, 2) NOT NULL,
                    reorder_point_tons NUMERIC(10, 2) NOT NULL,
                    average_daily_consumption NUMERIC(10, 2) NOT NULL,
                    max_lead_time_days INT NOT NULL,
                    max_budget_per_ton NUMERIC(12, 2) NOT NULL
                );

                CREATE TABLE suppliers (
                    vendor_id VARCHAR(100) PRIMARY KEY,
                    material_supplied VARCHAR(100) NOT NULL,
                    price_inr NUMERIC(12, 2) NOT NULL,
                    lead_time_days INT NOT NULL,
                    reliability NUMERIC(5, 2) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE
                );

                CREATE TABLE purchase_orders (
                    po_id SERIAL PRIMARY KEY,
                    agent_id VARCHAR(50) NOT NULL,
                    vendor_name VARCHAR(100) NOT NULL,
                    total_tonnage NUMERIC(10, 2) NOT NULL,
                    negotiated_unit_price NUMERIC(12, 2) NOT NULL,
                    total_landed_cost NUMERIC(14, 2) NOT NULL,
                    po_document TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE audit_log (
                    event_id SERIAL PRIMARY KEY,
                    agent_id VARCHAR(50) NOT NULL,
                    step_failed VARCHAR(100) NOT NULL,
                    error_message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE manager_notifications (
                    notif_id SERIAL PRIMARY KEY,
                    notif_type VARCHAR(50) NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    message TEXT NOT NULL,
                    material_name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE copilot_insights (
                    insight_id SERIAL PRIMARY KEY,
                    ai_source VARCHAR(100) DEFAULT 'CLAUDE_DESKTOP_MCP',
                    location VARCHAR(50) DEFAULT 'Mumbai',
                    category VARCHAR(100),
                    severity VARCHAR(30),
                    icon VARCHAR(30),
                    title TEXT,
                    message TEXT,
                    math_proof TEXT,
                    estimated_savings_inr NUMERIC(14, 2) DEFAULT 0.0,
                    action_label VARCHAR(120),
                    action_payload JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Seed Golden-Path Inventory
            inventory_seed = [
                # (material_name, current_stock, safety, reorder, daily_burn, max_sla, max_budget_ton)
                ("Bulk Wheat Flour", 38.0, 20.0, 35.0, 5.0, 7, 40000.00),   # 1 Shift (-5T) drops to 33T -> Auto-Heals (< ₹25L)
                ("Refined Sugar", 22.0, 10.0, 15.0, 3.0, 10, 45000.00),     # Healthy buffer
                ("Palm Oil", 20.0, 10.0, 18.0, 3.0, 5, 80000.00),           # 1 Shift (-3T) drops to 17T -> Auto-Heals (< ₹25L)
                ("Cocoa Beans", 18.0, 8.0, 15.0, 1.5, 14, 280000.00),       # Click -5T drops to 13T -> Escalates to Human (> ₹25L)
                ("Bulk Corn (Maize)", 30.0, 12.0, 20.0, 2.0, 7, 18000.00),  # Healthy buffer
                ("Corrugated Cartons", 25.0, 10.0, 18.0, 2.0, 4, 10000.00)  # Healthy buffer
            ]
            cur.executemany("""
                INSERT INTO inventory
                (material_name, current_stock_tons, safety_stock_tons, reorder_point_tons, average_daily_consumption, max_lead_time_days, max_budget_per_ton)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, inventory_seed)

            # 4. Seed Enterprise Suppliers (3 per commodity = 18 total)
            suppliers_seed = [
                ("Shakti Agro Mills Ltd.", "Bulk Wheat Flour", 35000.0, 6, 90.0, True),
                ("Deccan Roller Flour Mills", "Bulk Wheat Flour", 33000.0, 7, 84.0, True),
                ("Narmada Grain & Agritech", "Bulk Wheat Flour", 38000.0, 5, 96.0, True),

                ("Konkan Sugars Ltd.", "Refined Sugar", 41000.0, 8, 91.0, True),
                ("Baramati Cane Refineries", "Refined Sugar", 39500.0, 9, 85.0, True),
                ("Godavari Sugar Corp.", "Refined Sugar", 43500.0, 6, 96.0, True),

                ("Sahyadri Oils Ltd.", "Palm Oil", 74000.0, 4, 90.0, True),
                ("Adani Wilmar Industrial", "Palm Oil", 71500.0, 5, 86.0, True),
                ("Godrej Agrovet Palm Div.", "Palm Oil", 78000.0, 3, 97.0, True),

                ("Malabar Cocoa Estates", "Cocoa Beans", 255000.0, 11, 90.0, True),
                ("Nilgiri Craft Cocoa Ltd.", "Cocoa Beans", 246000.0, 13, 85.0, True),
                ("Olam Food Ingredients", "Cocoa Beans", 272000.0, 8, 97.0, True),

                ("Kaveri Maize & Starch Co.", "Bulk Corn (Maize)", 15800.0, 6, 91.0, True),
                ("Vidarbha Agro Corp.", "Bulk Corn (Maize)", 14900.0, 7, 85.0, True),
                ("Indus Grain Logistics", "Bulk Corn (Maize)", 16900.0, 4, 96.0, True),

                ("Horizon Packtech Ltd.", "Corrugated Cartons", 8900.0, 3, 92.0, True),
                ("Western India Corrugators", "Corrugated Cartons", 8400.0, 4, 86.0, True),
                ("Apex Kraft Packaging", "Corrugated Cartons", 9500.0, 2, 97.0, True)
            ]
            cur.executemany("""
                INSERT INTO suppliers (vendor_id, material_supplied, price_inr, lead_time_days, reliability, is_active)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, suppliers_seed)

            # 5. Seed Baseline Committed POs
            po_seed = [
                ("AGENT_FINANCE_01", "Shakti Agro Mills Ltd.", 25.0, 33610.0, 915250.0, "PO-SEED-001: 25T Bulk Wheat Flour"),
                ("AGENT_SYSTEM_AUTO", "Konkan Sugars Ltd.", 22.0, 39380.0, 894100.0, "PO-SEED-002: 22T Refined Sugar")
            ]
            cur.executemany("""
                INSERT INTO purchase_orders (agent_id, vendor_name, total_tonnage, negotiated_unit_price, total_landed_cost, po_document)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, po_seed)

            # 6. Seed 1 Baseline Blocked Security Threat
            cur.execute("""
                INSERT INTO audit_log (agent_id, step_failed, error_message)
                VALUES ('AGENT_INVENTORY_01', 'STEP_3_SEPARATION_OF_DUTIES', 'Role INVENTORY_MONITOR lacks financial commit authority.');
            """)

            # 7. Seed 4 Diverse Claude MCP Copilot Insights
            copilot_seed = [
                (
                    "CLAUDE_DESKTOP_MCP", "Mumbai", "SLAB_ARBITRAGE", "HIGH", "trend",
                    "Palm Oil Tier-2 Slab & Kandla Corridor Optimization",
                    "Stock is 20T (Reorder 18T). Consolidating next replenishment to 25T unlocks 2% wholesale slab with Sahyadri Oils Ltd.",
                    "25T × ₹74,000 × 2% Slab + Rail Modal Shift = ₹64,500 saved",
                    64500.00,
                    "Dispatch 25T Palm Oil",
                    json.dumps({
                        "material_name": "Palm Oil",
                        "required_tonnage": 25.0,
                        "inventory_urgency_days": 4,
                        "transport_distance_km": 610.0,
                        "budget_cap": 4000000.0,
                        "simulated_environment": "Mumbai",
                        "agent_id": "AGENT_FINANCE_01"
                    })
                ),
                (
                    "CLAUDE_DESKTOP_MCP", "Mumbai", "MODAL_ARBITRAGE", "HIGH", "boxes",
                    "Bulk Wheat Flour Indore → Mumbai Rail Arbitrage",
                    "38T on hand (7.6d cover). Pre-booking 25T via National Rail Cargo cuts freight by 55.6% vs highway road.",
                    "25T × ₹35,000 × 2% Slab + 585km Rail Savings = ₹54,060 saved",
                    54060.00,
                    "Dispatch 25T Wheat Flour",
                    json.dumps({
                        "material_name": "Bulk Wheat Flour",
                        "required_tonnage": 25.0,
                        "inventory_urgency_days": 5,
                        "transport_distance_km": 585.0,
                        "budget_cap": 4000000.0,
                        "simulated_environment": "Mumbai",
                        "agent_id": "AGENT_FINANCE_01"
                    })
                ),
                (
                    "CLAUDE_DESKTOP_MCP", "Mumbai", "HIGH_VALUE_HEDGE", "CRITICAL", "alert",
                    "Cocoa Beans Lead-Time Buffer (Kochi Corridor)",
                    "Fastest vendor SLA is 8–11 days while current buffer is nearing reorder threshold. Recommend 12T batch.",
                    "12T × ₹2,55,000 negotiated counter-offer + Rail = ₹91,800 saved",
                    91800.00,
                    "Dispatch 12T Cocoa Beans",
                    json.dumps({
                        "material_name": "Cocoa Beans",
                        "required_tonnage": 12.0,
                        "inventory_urgency_days": 3,
                        "transport_distance_km": 1150.0,
                        "budget_cap": 4000000.0,
                        "simulated_environment": "Mumbai",
                        "agent_id": "AGENT_FINANCE_01"
                    })
                ),
                (
                    "CLAUDE_DESKTOP_MCP", "Mumbai", "FREIGHT_OPTIMIZATION", "OPPORTUNITY", "coins",
                    "Bulk Corn (Maize) Nagpur Rail Hub Consolidation",
                    "790km Nagpur corridor offers high rail freight spread (₹2.00 vs ₹4.50/t-km) on a 30T batch.",
                    "30T × 790km × ₹2.50/t-km spread + 2% Slab = ₹68,730 saved",
                    68730.00,
                    "Dispatch 30T Bulk Corn",
                    json.dumps({
                        "material_name": "Bulk Corn (Maize)",
                        "required_tonnage": 30.0,
                        "inventory_urgency_days": 6,
                        "transport_distance_km": 790.0,
                        "budget_cap": 4000000.0,
                        "simulated_environment": "Mumbai",
                        "agent_id": "AGENT_FINANCE_01"
                    })
                )
            ]
            cur.executemany("""
                INSERT INTO copilot_insights
                (ai_source, location, category, severity, icon, title, message,
                 math_proof, estimated_savings_inr, action_label, action_payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, copilot_seed)

            # 8. Seed Clean Welcome Notification
            cur.execute("""
                INSERT INTO manager_notifications (notif_type, title, message, material_name)
                VALUES ('INFO', 'Demo Environment Reset & Ready', 'All 6 silos, 18 suppliers, and 4 Claude MCP insights initialized.', 'Bulk Wheat Flour');
            """)

            conn.commit()
    print("✅ PostgreSQL tables reset and seeded!")


def reset_running_fastapi_memory():
    """Resets the in-memory Autonomous Self-Healing state if uvicorn is currently running."""
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/auto-heal/toggle",
            data=json.dumps({"enabled": False, "reset_circuit_breaker": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                print("✅ FastAPI in-memory Circuit Breaker, Spend Counters & Cooldowns reset (Auto-Pilot DISARMED)!")
    except Exception:
        print("ℹ️  Note: Uvicorn server not detected on port 8000 (in-memory state will start fresh when you launch uvicorn).")


if __name__ == "__main__":
    reset_database()
    reset_running_fastapi_memory()
    print("\n🎯 DEMO READY! Your Golden Path:")
    print("  1. AI Copilot Tab -> Shows ₹2,79,090 Total Savings, 1 Critical Alert & 4 distinct material bars.")
    print("  2. Inventory Tab  -> Click 'Enable Auto-Pilot', then click 'Run 1 Production Shift'.")
    print("                       Watch Bulk Wheat Flour & Palm Oil auto-heal via AGENT_SYSTEM_AUTO (< ₹25L)!")
    print("  3. Inventory Tab  -> Click '-5T' on Cocoa Beans. Watch it pause in 'Pending Manager Approval' (> ₹25L)!")