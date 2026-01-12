#!/usr/bin/env python3
"""
Test script for Bakery Inventory Management System
This script tests all core functionality without requiring user interaction.
"""

import json
import os
import sys

# Import functions from bakery_inventory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bakery_inventory import (
    bakery_data,
    create_material,
    add_material_batch,
    get_material_total_quantity,
    create_recipe,
    produce_product,
    consume_material_fifo,
    save_data,
    load_data,
    DATA_FILE
)


def test_system():
    """Run comprehensive tests on the bakery inventory system."""

    print("="*80)
    print("🧪 BAKERY INVENTORY SYSTEM - AUTOMATED TEST")
    print("="*80)

    # Clean up any existing test data
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
        print("\n✓ Cleaned up existing data file")

    # Test 1: Create Materials
    print("\n" + "-"*80)
    print("TEST 1: Creating Raw Materials")
    print("-"*80)

    assert create_material("Flour", "kg", 10.0), "Failed to create Flour"
    assert create_material("Butter", "kg", 5.0), "Failed to create Butter"
    assert create_material("Sugar", "kg", 8.0), "Failed to create Sugar"
    assert create_material("Eggs", "dozen", 2.0), "Failed to create Eggs"

    print("✓ All materials created successfully")

    # Test 2: Add Material Batches (FIFO)
    print("\n" + "-"*80)
    print("TEST 2: Adding Material Batches (FIFO)")
    print("-"*80)

    assert add_material_batch("Flour", 50.0, 2.0, "2026-01-01"), "Failed to add Flour batch 1"
    assert add_material_batch("Flour", 30.0, 2.20, "2026-01-05"), "Failed to add Flour batch 2"
    assert add_material_batch("Butter", 20.0, 5.0, "2026-01-01"), "Failed to add Butter batch"
    assert add_material_batch("Sugar", 25.0, 1.5, "2026-01-01"), "Failed to add Sugar batch"
    assert add_material_batch("Eggs", 10.0, 3.0, "2026-01-01"), "Failed to add Eggs batch"

    flour_total = get_material_total_quantity("Flour")
    assert flour_total == 80.0, f"Flour total should be 80, got {flour_total}"
    print(f"✓ Flour total: {flour_total} kg (across 2 batches)")

    # Test 3: Create Recipes
    print("\n" + "-"*80)
    print("TEST 3: Creating Product Recipes")
    print("-"*80)

    croissant_ingredients = {
        "Flour": 0.5,
        "Butter": 0.2,
        "Sugar": 0.1
    }
    assert create_recipe("Croissant", croissant_ingredients, 12), "Failed to create Croissant recipe"

    cake_ingredients = {
        "Flour": 1.0,
        "Butter": 0.5,
        "Sugar": 0.8,
        "Eggs": 0.5
    }
    assert create_recipe("Cake", cake_ingredients, 1), "Failed to create Cake recipe"

    print("✓ All recipes created successfully")

    # Test 4: Test FIFO Material Consumption
    print("\n" + "-"*80)
    print("TEST 4: Testing FIFO Material Consumption")
    print("-"*80)

    print("\nBefore consumption:")
    print(f"  Flour batches: {len(bakery_data['materials']['Flour']['batches'])}")
    for i, batch in enumerate(bakery_data['materials']['Flour']['batches'], 1):
        print(f"    Batch {i}: {batch['quantity']} kg (Date: {batch['purchase_date']})")

    # Consume 60kg flour (should consume entire first batch + 10kg from second)
    success, message = consume_material_fifo("Flour", 60.0)
    assert success, f"Failed to consume flour: {message}"
    print(f"\n✓ {message}")

    print("\nAfter consuming 60kg:")
    print(f"  Flour batches: {len(bakery_data['materials']['Flour']['batches'])}")
    for i, batch in enumerate(bakery_data['materials']['Flour']['batches'], 1):
        print(f"    Batch {i}: {batch['quantity']} kg (Date: {batch['purchase_date']})")

    remaining_flour = get_material_total_quantity("Flour")
    assert remaining_flour == 20.0, f"Remaining flour should be 20kg, got {remaining_flour}kg"
    assert len(bakery_data['materials']['Flour']['batches']) == 1, "Should have 1 batch remaining"

    print(f"\n✓ FIFO working correctly: {remaining_flour} kg remaining in 1 batch")

    # Test 5: Production with Automatic Material Deduction
    print("\n" + "-"*80)
    print("TEST 5: Production with Automatic Material Deduction")
    print("-"*80)

    # Add more flour for production test
    add_material_batch("Flour", 50.0, 2.30, "2026-01-10")

    print("\nBefore production:")
    print(f"  Flour: {get_material_total_quantity('Flour')} kg")
    print(f"  Butter: {get_material_total_quantity('Butter')} kg")
    print(f"  Sugar: {get_material_total_quantity('Sugar')} kg")

    # Produce 2 batches of croissants (needs 1kg flour, 0.4kg butter, 0.2kg sugar)
    assert produce_product("Croissant", 2), "Failed to produce croissants"

    print("\nAfter producing 2 batches of croissants (24 units):")
    print(f"  Flour: {get_material_total_quantity('Flour')} kg")
    print(f"  Butter: {get_material_total_quantity('Butter')} kg")
    print(f"  Sugar: {get_material_total_quantity('Sugar')} kg")
    print(f"  Croissants produced: {bakery_data['products']['Croissant']['quantity']} units")

    assert bakery_data['products']['Croissant']['quantity'] == 24, "Should have 24 croissants"
    assert get_material_total_quantity('Flour') == 69.0, "Flour should be 69kg after production"

    print("✓ Production successful with correct material deduction")

    # Test 6: Insufficient Stock Handling
    print("\n" + "-"*80)
    print("TEST 6: Testing Insufficient Stock Handling")
    print("-"*80)

    # Try to produce 100 batches of cakes (should fail)
    result = produce_product("Cake", 100)
    assert not result, "Should fail when insufficient materials"
    print("✓ System correctly prevents production with insufficient materials")

    # Test 7: Data Persistence
    print("\n" + "-"*80)
    print("TEST 7: Testing Data Persistence")
    print("-"*80)

    # Save current data
    save_data()
    print("✓ Data saved to file")

    # Store current state
    croissant_qty = bakery_data['products']['Croissant']['quantity']

    # Verify data was written to file
    with open(DATA_FILE, 'r') as f:
        saved_data = json.load(f)

    assert 'Croissant' in saved_data['products'], "Croissant not found in saved file"
    assert saved_data['products']['Croissant']['quantity'] == croissant_qty, "Croissant quantity mismatch in file"
    print(f"✓ Data persistence verified: {croissant_qty} croissants saved to file")

    # Test reload
    import bakery_inventory
    bakery_inventory.bakery_data.clear()
    load_data()
    # After load_data, bakery_data is updated in the module
    from bakery_inventory import bakery_data as reloaded_data
    assert 'Croissant' in reloaded_data['products'], "Croissant not found after reload"
    print("✓ Data successfully reloaded from file")

    # Test 8: Low Stock Detection
    print("\n" + "-"*80)
    print("TEST 8: Testing Low Stock Detection")
    print("-"*80)

    # Use the reloaded data reference
    from bakery_inventory import bakery_data as active_data

    # Consume butter to trigger low stock alert (threshold is 5kg)
    consume_material_fifo("Butter", 16.0)
    butter_remaining = get_material_total_quantity("Butter")
    butter_threshold = active_data['materials']['Butter']['min_threshold']

    print(f"  Butter remaining: {butter_remaining} kg")
    print(f"  Butter threshold: {butter_threshold} kg")

    if butter_remaining < butter_threshold:
        print("✓ Low stock alert would be triggered for Butter")
    else:
        print("  (Butter still above threshold)")

    # Final Summary
    print("\n" + "="*80)
    print("📊 FINAL INVENTORY SUMMARY")
    print("="*80)

    print("\nRaw Materials:")
    for material_name, material_data in active_data['materials'].items():
        total = get_material_total_quantity(material_name)
        print(f"  • {material_name}: {total} {material_data['unit']} "
              f"(Min: {material_data['min_threshold']} {material_data['unit']})")

    print("\nFinished Products:")
    for product_name, product_data in active_data['products'].items():
        print(f"  • {product_name}: {product_data['quantity']} units")

    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED SUCCESSFULLY!")
    print("="*80)

    print("\n✓ The bakery inventory system is fully functional!")
    print("✓ FIFO material tracking works correctly")
    print("✓ Production deducts materials automatically")
    print("✓ Data persistence is working")
    print("✓ Error handling prevents invalid operations")

    return True


if __name__ == "__main__":
    try:
        test_system()
        print("\n🎉 Test suite completed successfully!\n")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
