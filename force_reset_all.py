import chromadb
import os
from dotenv import load_dotenv

load_dotenv()

client = chromadb.CloudClient(
    api_key=os.getenv("CHROMADB_API_KEY"),
    tenant=os.getenv("CHROMADB_TENANT"),
    database=os.getenv("CHROMADB_DATABASE"),
)

print("Listing all collections...")
collections = client.list_collections()
print(f"Found {len(collections)} collections:")
for col in collections:
    print(f"  - {col.name}")

print("\nDeleting all collections...")
for col in collections:
    try:
        client.delete_collection(col.name)
        print(f"[OK] Deleted {col.name}")
    except Exception as e:
        print(f"[ERROR] Could not delete {col.name}: {e}")

print("\nVerifying deletion...")
remaining = client.list_collections()
print(f"Remaining collections: {len(remaining)}")
if remaining:
    for col in remaining:
        print(f"  - {col.name}")
else:
    print("All collections successfully deleted!")
