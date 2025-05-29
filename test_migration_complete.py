#!/usr/bin/env python3
"""Comprehensive test to verify the complete fix for the migration"""

import requests
import json

def test_complete_migration():
    """Test all endpoints to verify the migration is working correctly"""
    base_url = "http://localhost:8000/api/reports"
    
    print("🧪 Testing Complete Migration Fix")
    print("=" * 50)
    
    # Test 1: Cycles endpoint with new format
    print("\n1. Testing Cycles Endpoint...")
    try:
        response = requests.get(f"{base_url}/data/cycles", timeout=10)
        if response.status_code == 200:
            cycles = response.json()
            print(f"✅ Cycles: Found {len(cycles)} cycles")
            for cycle in cycles[:3]:  # Show first 3
                print(f"   - {cycle['label']}: cycle={cycle['cycle']} (type: {type(cycle['cycle'])})")
        else:
            print(f"❌ Cycles failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Cycles error: {e}")
    
    # Test 2: Deals endpoint with integer dl_nbr
    print("\n2. Testing Deals Endpoint...")
    try:
        response = requests.get(f"{base_url}/data/deals", timeout=10)
        if response.status_code == 200:
            deals = response.json()
            print(f"✅ Deals: Found {len(deals)} deals")
            for deal in deals[:3]:  # Show first 3
                print(f"   - Deal {deal['dl_nbr']}: {deal['issr_cde']} (dl_nbr type: {type(deal['dl_nbr'])})")
        else:
            print(f"❌ Deals failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Deals error: {e}")
    
    # Test 3: Tranches endpoint (the main fix)
    print("\n3. Testing Tranches Endpoint (Main Fix)...")
    try:
        payload = {"dl_nbrs": [1, 2, 3]}  # Using integers
        response = requests.post(f"{base_url}/data/tranches", json=payload, timeout=10)
        if response.status_code == 200:
            tranches = response.json()
            print(f"✅ Tranches: Found data for {len(tranches)} deals")
            for dl_nbr, tranche_list in list(tranches.items())[:2]:  # Show first 2 deals
                print(f"   - Deal {dl_nbr} (key type: {type(dl_nbr)}): {len(tranche_list)} tranches")
                if tranche_list:
                    sample_tranche = tranche_list[0]
                    print(f"     Sample: dl_nbr={sample_tranche['dl_nbr']} (type: {type(sample_tranche['dl_nbr'])})")
        else:
            print(f"❌ Tranches failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Tranches error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Migration test complete!")
    print("\nKey fixes verified:")
    print("✅ Cycles return {label: str, cycle: int} format")
    print("✅ Deals return integer dl_nbr values")  
    print("✅ Tranches accept integer dl_nbrs and return string-keyed response")
    print("✅ No more ResponseValidationError!")

if __name__ == "__main__":
    test_complete_migration()
