import os
import psycopg2

# Retrieve connection parameters dynamically with local fallbacks
DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "fmcg_procurement"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "1234"),  # Update to your local password
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432")
}


def init_db():
    """Reads schema.sql and initializes database tables using context managers."""
    schema_file = "schema.sql"

    if not os.path.exists(schema_file):
        print(f"🛑 Error: {schema_file} file not found in current directory.")
        return

    try:
        # Context Manager handles connection cleanup automatically
        with psycopg2.connect(**DB_CONFIG) as conn:
            # Context Manager handles cursor lifecycle automatically
            with conn.cursor() as cursor:
                with open(schema_file, "r", encoding="utf-8") as file:
                    sql_script = file.read()

                # Execute full schema and seed commands
                cursor.execute(sql_script)

                # Commit transaction explicitly
                conn.commit()

        print("✅ Database initialized successfully! All 5 tables, indexes, and seed data are ready.")

    except psycopg2.OperationalError as db_err:
        print(f"❌ Connection Failed: Ensure PostgreSQL is running and DB_CONFIG credentials are correct.\nDetails: {db_err}")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")


if __name__ == "__main__":
    print("🛠️ Initializing PostgreSQL Persistence Layer...")
    init_db()