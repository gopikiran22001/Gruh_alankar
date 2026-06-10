import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("CHROMADB_API_KEY")
tenant = os.getenv("CHROMADB_TENANT")
database = os.getenv("CHROMADB_DATABASE")

base_url = "https://api.trychroma.com"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "X-Chroma-Tenant": tenant,
    "X-Chroma-Database": database
}

collections = ["user_memory", "conversation_memory", "design_memory", "style_memory"]

print(f"Deleting collections from tenant: {tenant}, database: {database}\n")

for collection_name in collections:
    try:
        # Try DELETE request
        url = f"{base_url}/api/v1/collections/{collection_name}"
        response = requests.delete(url, headers=headers, params={"tenant": tenant, "database": database})
        
        if response.status_code in [200, 204]:
            print(f"[OK] Deleted {collection_name}")
        elif response.status_code == 404:
            print(f"[SKIP] {collection_name} not found")
        else:
            print(f"[ERROR] {collection_name}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] {collection_name}: {e}")

print("\n" + "="*60)
print("IMPORTANT: If you see errors above, please:")
print("1. Go to https://app.trychroma.com/")
print("2. Log in to your account")
print("3. Navigate to your database 'gruhaAlankar'")
print("4. Manually delete these collections:")
for col in collections:
    print(f"   - {col}")
print("="*60)
