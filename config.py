"""
config.py — Central configuration for the AI Engine.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_DIR = os.path.join(BASE_DIR, "chroma_db")

# 🧠 RAG Configuration (NEW)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "fmcg_policy_collection"

# Business Logic Caps (Policy v4)
MAX_TRANSACTION_BUDGET_INR = 4000000.00  # INR 40 Lakhs
MAX_NEGOTIATION_ROUNDS = 3

# Approved Catalog
APPROVED_CATALOG = [
    "Bulk Wheat Flour", 
    "Refined Sugar", 
    "Palm Oil", 
    "Cocoa Beans", 
    "Bulk Corn (Maize)", 
    "Corrugated Cartons"
]

# SLA Lead Times (Mapped to DB schema)
MATERIAL_SLAS = {
    "Bulk Wheat Flour": 7,
    "Refined Sugar": 10,
    "Palm Oil": 5,
    "Cocoa Beans": 14,
    "Bulk Corn (Maize)": 7,
    "Corrugated Cartons": 4
}

# 🔗 CONNECTION POINT FOR MEMBER 2
SUPPLIER_API_URL = "http://127.0.0.1:8000/supplier/counteroffer"