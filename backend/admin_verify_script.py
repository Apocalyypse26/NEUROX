#!/usr/bin/env python3
"""
Admin Verification Test Script
Usage: python test_admin_verify.py <your_jwt_token>
"""

import sys
import httpx
import json
import asyncio

async def test_admin_verify(token: str):
    base_url = "http://localhost:8000"
    
    # Test 1: Admin Verify
    print("\n" + "="*60)
    print("TEST 1: Admin Verification")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{base_url}/api/admin/verify",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("is_admin"):
                    print("\n✅ ADMIN VERIFICATION: SUCCESS!")
                    print(f"   User ID: {data.get('user_id')}")
                    print(f"   Is Admin: {data.get('is_admin')}")
                else:
                    print("\n❌ ADMIN VERIFICATION: FAILED")
                    print("   User is not in admin_users table")
            else:
                print(f"\n❌ ERROR: {response.json()}")
                
    except Exception as e:
        print(f"\n❌ CONNECTION ERROR: {e}")
        print("   Make sure backend is running: cd backend && python main.py")
    
    # Test 2: Get All Uploads (Admin Only)
    print("\n" + "="*60)
    print("TEST 2: Get All Uploads (Admin Only)")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{base_url}/api/admin/uploads",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS! Found {data.get('count', 0)} uploads")
                if data.get('uploads'):
                    print(f"   First upload: {data['uploads'][0].get('file_name', 'Unknown')}")
            elif response.status_code == 403:
                print("❌ ACCESS DENIED: Not an admin")
            else:
                print(f"❌ ERROR: {response.json()}")
                
    except Exception as e:
        print(f"\n❌ CONNECTION ERROR: {e}")
    
    # Test 3: Get Admin Stats
    print("\n" + "="*60)
    print("TEST 3: Get Admin Statistics")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{base_url}/api/admin/stats",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS!")
                print(f"   Total Uploads: {data.get('total_uploads', 0)}")
                print(f"   Total Projects: {data.get('total_projects', 0)}")
            elif response.status_code == 403:
                print("❌ ACCESS DENIED: Not an admin")
            else:
                print(f"❌ ERROR: {response.json()}")
                
    except Exception as e:
        print(f"\n❌ CONNECTION ERROR: {e}")
    
    print("\n" + "="*60)
    print("TESTS COMPLETE")
    print("="*60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Missing JWT token!")
        print("\nUsage:")
        print("  python test_admin_verify.py <your_jwt_token>")
        print("\nTo get your JWT token:")
        print("1. Log into NEUROX in your browser")
        print("2. Open Developer Tools (F12) -> Console")
        print("3. Run: localStorage.getItem('supabase-auth-token')")
        print("4. Copy the 'access_token' from the JSON response")
        sys.exit(1)
    
    token = sys.argv[1]
    print(f"Testing with token: {token[:50]}...")
    asyncio.run(test_admin_verify(token))
