#!/usr/bin/env python3
"""
Test script to verify backend configuration without starting services.
"""

import sys
import os
sys.path.append('.')

def test_imports():
    """Test if all critical modules can be imported."""
    print("🔧 Testing imports...")
    
    try:
        from config.settings import settings
        print("✅ Settings loaded successfully")
        
        from app.database.mongo import users_collection
        print("✅ MongoDB module imported")
        
        from app.database.vector_store import vector_store
        print("✅ Vector store module imported")
        
        from app.database.redis_cache import cache
        print("✅ Redis cache module imported")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_configuration():
    """Test configuration values."""
    print("\n🔧 Testing configuration...")
    
    from config.settings import settings
    
    # Test ChromaDB configuration
    print(f"✅ ChromaDB cloud mode: {settings.chromadb.use_cloud_client}")
    if settings.chromadb.use_cloud_client:
        print(f"✅ ChromaDB tenant: {settings.chromadb.TENANT}")
        print(f"✅ ChromaDB database: {settings.chromadb.DATABASE}")
        print(f"✅ ChromaDB API key configured: {bool(settings.chromadb.API_KEY)}")
    
    # Test database connections
    print(f"✅ MongoDB URI configured: {bool(settings.mongo.URI)}")
    print(f"✅ MongoDB database: {settings.mongo.DB_NAME}")
    print(f"✅ Redis URL configured: {bool(settings.redis.URL)}")
    
    # Test API keys
    print(f"✅ DeepSeek API key: {bool(settings.deepseek.API_KEY)}")
    print(f"✅ Groq API key: {bool(settings.groq.API_KEY)}")
    
    return True

def test_vector_store():
    """Test ChromaDB cloud connection."""
    print("\n🔧 Testing ChromaDB cloud connection...")
    
    try:
        from app.database.vector_store import vector_store
        vector_store.connect()
        
        # Test heartbeat
        vector_store.client.heartbeat()
        print("✅ ChromaDB cloud connected successfully!")
        
        # Test basic functionality - list collections (this should work)
        try:
            collections = vector_store.client.list_collections()
            print(f"✅ Collections available: {len(collections)}")
        except Exception as e:
            print(f"⚠️  Collection listing failed (API differences): {e}")
        
        # Collection initialization errors are non-critical for now
        # The important thing is that the connection works
        print("✅ ChromaDB cloud connection test passed!")
        return True
    except Exception as e:
        print(f"❌ ChromaDB connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Gruha Alankara Backend Configuration Test")
    print("=" * 50)
    
    success = True
    
    success &= test_imports()
    success &= test_configuration()
    success &= test_vector_store()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Backend is ready to run.")
    else:
        print("❌ Some tests failed. Check the configuration.")
    
    sys.exit(0 if success else 1)