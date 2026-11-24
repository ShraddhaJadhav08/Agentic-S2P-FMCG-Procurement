"""
policy_search.py — Read-only semantic search over policy vector memory.
"""
import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Importing the synchronized variables to prevent the empty database loophole
from config import DB_DIR, EMBEDDING_MODEL_NAME, COLLECTION_NAME

_db = None

def search_purchasing_policy(query: str, top_k: int = 2) -> str:
    global _db
    
    # Lazy-load the database only on the first query
    if not _db:
        if not os.path.exists(DB_DIR):
            return "Vector DB not found. Run ingest.py first."
        
        _db = Chroma(
            persist_directory=DB_DIR, 
            embedding_function=HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME),
            collection_name=COLLECTION_NAME 
        )
    
    results = _db.similarity_search(query, k=top_k)
    
    if not results:
        return "No matching policy text found in vector memory."
        
    return "\n\n".join([" ".join(doc.page_content.split()) for doc in results])

# --- QUICK TEST BLOCK ---
if __name__ == "__main__":
    print("🔍 Testing semantic search engine...\n")
    test_query = "What is the maximum budget limit for a single transaction?"
    print(f"Q: {test_query}")
    print("-" * 50)
    print(search_purchasing_policy(test_query))
    print("-" * 50)