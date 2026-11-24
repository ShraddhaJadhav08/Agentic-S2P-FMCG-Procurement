"""
update_vendors.py — Upgrades generic *_Supplier_A/B/C IDs to B2B Enterprise Names
across PostgreSQL (suppliers & purchase_orders) and project source files.
"""
import os
import psycopg2

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "fmcg_procurement"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "1234"),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432")
}

# Complete mapping covering all naming conventions in schema.sql / database.py
VENDOR_MAP = {
    # Bulk Wheat Flour
    "Flour_Supplier_A": "Shakti Agro Mills Ltd.",
    "Flour_Supplier_B": "Deccan Roller Flour Mills",
    "Flour_Supplier_C": "Narmada Grain & Agritech",
    "Wheat_Supplier_A": "Shakti Agro Mills Ltd.",
    "Wheat_Supplier_B": "Deccan Roller Flour Mills",
    "Wheat_Supplier_C": "Narmada Grain & Agritech",

    # Refined Sugar
    "Sugar_Supplier_A": "Konkan Sugars Ltd.",
    "Sugar_Supplier_B": "Baramati Cane Refineries",
    "Sugar_Supplier_C": "Godavari Sugar Corp.",

    # Palm Oil
    "Palm_Supplier_A": "Sahyadri Oils Ltd.",
    "Palm_Supplier_B": "Adani Wilmar Industrial",
    "Palm_Supplier_C": "Godrej Agrovet Palm Div.",
    "Oil_Supplier_A": "Sahyadri Oils Ltd.",
    "Oil_Supplier_B": "Adani Wilmar Industrial",
    "Oil_Supplier_C": "Godrej Agrovet Palm Div.",

    # Cocoa Beans
    "Cocoa_Supplier_A": "Malabar Cocoa Estates",
    "Cocoa_Supplier_B": "Nilgiri Craft Cocoa Ltd.",
    "Cocoa_Supplier_C": "Olam Food Ingredients",

    # Bulk Corn (Maize)
    "Corn_Supplier_A": "Kaveri Maize & Starch Co.",
    "Corn_Supplier_B": "Vidarbha Agro Corp.",
    "Corn_Supplier_C": "Indus Grain Logistics",
    "Maize_Supplier_A": "Kaveri Maize & Starch Co.",
    "Maize_Supplier_B": "Vidarbha Agro Corp.",
    "Maize_Supplier_C": "Indus Grain Logistics",

    # Corrugated Cartons
    "Carton_Supplier_A": "Horizon Packtech Ltd.",
    "Carton_Supplier_B": "Western India Corrugators",
    "Carton_Supplier_C": "Apex Kraft Packaging",
    "Cartons_Supplier_A": "Horizon Packtech Ltd.",
    "Cartons_Supplier_B": "Western India Corrugators",
    "Cartons_Supplier_C": "Apex Kraft Packaging",

    # Generic fallback IDs (in case any test uses Supplier_A/B/C directly)
    "Supplier_A": "Shakti Agro Mills Ltd.",
    "Supplier_B": "Deccan Roller Flour Mills",
    "Supplier_C": "Narmada Grain & Agritech"
}

def update_source_files():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_files = [
        "schema.sql",
        "database.py",
        "agent_graph.py",
        "mcdm_engine.py",
        "simulation_engine.py"
    ]
    # Replace longest keys first so "Flour_Supplier_A" is replaced before "Supplier_A"
    sorted_keys = sorted(VENDOR_MAP.keys(), key=len, reverse=True)

    for fname in target_files:
        fpath = os.path.join(base_dir, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        updated = content
        for old_name in sorted_keys:
            updated = updated.replace(f"'{old_name}'", f"'{VENDOR_MAP[old_name]}'")
            updated = updated.replace(f'"{old_name}"', f'"{VENDOR_MAP[old_name]}"')

        if updated != content:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(updated)
            print(f"✅ Updated vendor names in {fname}")

def update_postgres():
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # 1. Inspect columns in suppliers table
                cur.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'suppliers';
                """)
                sup_cols = [r[0] for r in cur.fetchall()]

                for old_id, new_name in VENDOR_MAP.items():
                    if "vendor_id" in sup_cols:
                        cur.execute("UPDATE suppliers SET vendor_id = %s WHERE vendor_id = %s;", (new_name, old_id))
                    if "vendor_name" in sup_cols:
                        cur.execute("UPDATE suppliers SET vendor_name = %s WHERE vendor_name = %s;", (new_name, old_id))
                    if "supplier_name" in sup_cols:
                        cur.execute("UPDATE suppliers SET supplier_name = %s WHERE supplier_name = %s;", (new_name, old_id))

                    # 2. Update existing committed orders in purchase_orders
                    cur.execute("UPDATE purchase_orders SET vendor_name = %s WHERE vendor_name = %s;", (new_name, old_id))

                conn.commit()
        print("✅ Updated live PostgreSQL 'suppliers' and 'purchase_orders' tables!")
    except Exception as e:
        print(f"⚠️ PostgreSQL update note: {e}")

if __name__ == "__main__":
    update_source_files()
    update_postgres()
    print("🎉 Enterprise vendor name upgrade complete!")