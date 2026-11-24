"""
ingest.py — Builds ChromaDB vector store from the procurement policy document.
"""
import os
import sys
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Centralize configuration imports to prevent mismatch bugs
from config import DATA_DIR, DB_DIR, EMBEDDING_MODEL_NAME, COLLECTION_NAME


def build_db():
    # Make sure this filename matches your active framework PDF in your data/ folder
    pdf_path = os.path.join(DATA_DIR, "fmcg_procurement_policy.pdf")

    if not os.path.exists(pdf_path):
        print(f"⚠️ No PDF found. Please place your framework PDF in: {DATA_DIR}")
        print(f"💡 Expected path: {pdf_path}")
        return

    print(f"📄 Loading policy PDF from: {pdf_path}")
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    # Chunking strategy: 500 characters with 50 character overlap for clean semantic retrieval
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(docs)
    print(f"✂️ Created {len(chunks)} text chunks.")

    print(f"🧠 Initializing HuggingFace embedding model: '{EMBEDDING_MODEL_NAME}'...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    print(f"💾 Persisting vectors to ChromaDB collection '{COLLECTION_NAME}' at: {DB_DIR}")
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_DIR,
        collection_name=COLLECTION_NAME
    )
    print("✅ Vector DB Built and Synchronized Successfully!")


if __name__ == "__main__":
    build_db()