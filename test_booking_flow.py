#!/usr/bin/env python3
"""
Test booking creation and listing flow.
"""

import asyncio
from app.agents.booking_agent import BookingAgent
from app.agents.schemas import AgentTask
from config.constants import AgentName
from config.logging_config import setup_logging

setup_logging()

async def test_booking_flow():
    print("\n" + "="*70)
    print("🧪 Testing Booking Creation and Listing Flow")
    print("="*70 + "\n")
    
    agent = BookingAgent()
    test_user_id = "test_user_booking_123"
    
    # Test 1: Create a booking
    print("📋 Test 1: Create Booking")
    create_task = AgentTask(
        task_id="test_create_001",
        task_type="create_booking",
        agent_name=AgentName.BOOKING,
        parameters={
            "user_id": test_user_id,
            "products": [
                {
                    "product_id": "prod_001",
                    "name": "Modern Sofa",
                    "price": 15000,
                    "quantity": 1
                },
                {
                    "product_id": "prod_002",
                    "name": "Coffee Table",
                    "price": 5000,
                    "quantity": 2
                }
            ],
            "payment_info": {
                "method": "card",
                "transaction_id": "txn_test_001"
            },
            "delivery_address": {
                "street": "123 Test Street",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001"
            }
        }
    )
    
    result = await agent.run(create_task)
    
    if result.is_success:
        print("✅ Booking created successfully!")
        print(f"   Booking ID: {result.data.get('booking_id')}")
        print(f"   Status: {result.data.get('status')}")
        print(f"   Total: ₹{result.data.get('total_inr')}")
        print(f"   Items: {result.data.get('item_count')}")
        
        booking_details = result.data.get('booking')
        if booking_details:
            print(f"   Created At: {booking_details.get('created_at')}")
            print(f"   Full booking data included: ✅")
        else:
            print(f"   ⚠️ Warning: Full booking data not included in response")
        
        booking_id = result.data.get('booking_id')
    else:
        print("❌ Failed to create booking:")
        print(f"   Errors: {result.errors}")
        return
    
    print()
    
    # Test 2: List bookings
    print("📋 Test 2: List Bookings")
    list_task = AgentTask(
        task_id="test_list_001",
        task_type="list_bookings",
        agent_name=AgentName.BOOKING,
        parameters={
            "user_id": test_user_id,
        }
    )
    
    result = await agent.run(list_task)
    
    if result.is_success:
        bookings = result.data.get('bookings', [])
        print(f"✅ Found {len(bookings)} booking(s)")
        
        for i, booking in enumerate(bookings, 1):
            print(f"\n   Booking {i}:")
            print(f"   - ID: {booking.get('_id')}")
            print(f"   - Status: {booking.get('status')}")
            print(f"   - Total: ₹{booking.get('total_inr')}")
            print(f"   - Products: {len(booking.get('products', []))}")
            print(f"   - Created: {booking.get('created_at')}")
    else:
        print("❌ Failed to list bookings:")
        print(f"   Errors: {result.errors}")
        return
    
    print()
    
    # Test 3: Track specific booking
    print("📋 Test 3: Track Booking")
    track_task = AgentTask(
        task_id="test_track_001",
        task_type="track_order",
        agent_name=AgentName.BOOKING,
        parameters={
            "booking_id": booking_id,
        }
    )
    
    result = await agent.run(track_task)
    
    if result.is_success:
        print(f"✅ Tracking info retrieved")
        print(f"   Current Status: {result.data.get('current_status')}")
        print(f"   Total: ₹{result.data.get('total_inr')}")
        
        history = result.data.get('status_history', [])
        print(f"   Status History: {len(history)} entries")
        for entry in history:
            print(f"     - {entry.get('status')}: {entry.get('note')} at {entry.get('timestamp')}")
    else:
        print("❌ Failed to track booking:")
        print(f"   Errors: {result.errors}")
    
    print("\n" + "="*70)
    print("✅ All booking flow tests completed!")
    print("="*70 + "\n")
    
    # Cleanup
    print("🧹 Cleaning up test data...")
    from app.database.mongo import delete_one
    from config.constants import MongoCollection
    
    delete_one(MongoCollection.BOOKINGS, {"_id": booking_id})
    print("✅ Cleanup complete\n")

if __name__ == "__main__":
    asyncio.run(test_booking_flow())
