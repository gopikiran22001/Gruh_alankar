import chromadb
import os
from dotenv import load_dotenv

load_dotenv()

client = chromadb.CloudClient(
    api_key=os.getenv("CHROMADB_API_KEY"),
    tenant=os.getenv("CHROMADB_TENANT"),
    database=os.getenv("CHROMADB_DATABASE"),
)

collections_to_reset = ["user_memory", "conversation_memory", "design_memory", "style_memory"]

for collection_name in collections_to_reset:
    try:
        client.delete_collection(collection_name)
        print(f"[OK] Deleted {collection_name}")
    except Exception as e:
        print(f"[ERROR] Could not delete {collection_name}: {e}")

print("\nCollections reset. Restart your application to recreate them.")
