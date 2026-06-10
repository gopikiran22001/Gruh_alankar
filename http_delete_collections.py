import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("CHROMADB_API_KEY")
tenant = os.getenv("CHROMADB_TENANT")
database = os.getenv("CHROMADB_DATABASE")

# ChromaDB Cloud API endpoint
base_url = f"https://api.trychroma.com"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

collections_to_delete = ["user_memory", "conversation_memory", "design_memory", "style_memory"]

print("Deleting collections via HTTP API...")
for collection_name in collections_to_delete:
    try:
        url = f"{base_url}/api/v1/collections/{collection_name}?tenant={tenant}&database={database}"
        response = requests.delete(url, headers=headers)
        
        if response.status_code == 200:
            print(f"[OK] Deleted {collection_name}")
        elif response.status_code == 404:
            print(f"[SKIP] {collection_name} does not exist")
        else:
            print(f"[ERROR] {collection_name}: HTTP {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] {collection_name}: {e}")

print("\nDone! Restart your application.")
