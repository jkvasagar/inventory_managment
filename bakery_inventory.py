#!/usr/bin/env python3
"""
Bakery Inventory Management System
A comprehensive CLI tool for managing bakery inventory, recipes, production, and sales.
Features:
- FIFO-based raw material management with batch tracking
- Recipe management for finished products
- Production tracking with automatic material deduction
- Low stock alerts
- Admin, Inventory, and POS interfaces
- JSON-based data persistence
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ============================================================================
# GLOBAL DATA STRUCTURE
# ============================================================================

# Main data structure to hold all bakery data
bakery_data = {
    "materials": {},  # {material_name: {"unit": str, "min_threshold": float, "batches": [...]}}
    "recipes": {},    # {product_name: {"ingredients": {material_name: quantity}, "batch_size": int}}
    "products": {}    # {product_name: {"quantity": int, "price": float}}
}

DATA_FILE = "bakery_data.json"


# ============================================================================
# DATA PERSISTENCE FUNCTIONS
# ============================================================================

def load_data():
    """
    Load bakery data from JSON file.
    Creates a new file with default structure if it doesn't exist.
    """
    global bakery_data

    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                bakery_data = json.load(f)
                print(f"✓ Data loaded successfully from {DATA_FILE}")
        else:
            print(f"! No existing data file found. Starting with empty inventory.")
            save_data()
    except json.JSONDecodeError:
        print(f"✗ Error: {DATA_FILE} is corrupted. Starting with empty inventory.")
        bakery_data = {
            "materials": {},
            "recipes": {},
            "products": {}
        }
        save_data()
    except Exception as e:
        print(f"✗ Error loading data: {e}")


def save_data():
    """
    Save current bakery data to JSON file.
    """
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(bakery_data, f, indent=4)
        print(f"✓ Data saved successfully to {DATA_FILE}")
    except Exception as e:
        print(f"✗ Error saving data: {e}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')


def pause():
    """Pause execution until user presses Enter."""
    input("\nPress Enter to continue...")


def get_valid_input(prompt: str, input_type=str, allow_empty=False):
    """
    Get validated input from user.

    Args:
        prompt: The prompt to display
        input_type: Expected type (str, int, float)
        allow_empty: Whether empty input is allowed

    Returns:
        Validated input of the specified type
    """
    while True:
        try:
            user_input = input(prompt).strip()

            if not user_input and allow_empty:
                return None

            if not user_input:
                print("✗ Input cannot be empty. Please try again.")
                continue

            if input_type == str:
                return user_input
            elif input_type == int:
                return int(user_input)
            elif input_type == float:
                return float(user_input)

        except ValueError:
            print(f"✗ Invalid input. Please enter a valid {input_type.__name__}.")
        except KeyboardInterrupt:
            print("\n✗ Operation cancelled by user.")
            return None


def get_current_date():
    """Get current date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")


# ============================================================================
# RAW MATERIAL MANAGEMENT (FIFO)
# ============================================================================

def add_material_batch(material_name: str, quantity: float, cost_per_unit: float,
                       purchase_date: Optional[str] = None):
    """
    Add a new batch of raw material using FIFO method.

    Args:
        material_name: Name of the material
        quantity: Quantity to add
        cost_per_unit: Cost per unit for this batch
        purchase_date: Purchase date (defaults to today)
    """
    if purchase_date is None:
        purchase_date = get_current_date()

    # Create material entry if it doesn't exist
    if material_name not in bakery_data["materials"]:
        print(f"✗ Material '{material_name}' not found. Please add it first.")
        return False

    # Add new batch to the material's batch list
    batch = {
        "quantity": quantity,
        "cost_per_unit": cost_per_unit,
        "purchase_date": purchase_date
    }

    bakery_data["materials"][material_name]["batches"].append(batch)
    print(f"✓ Added {quantity} {bakery_data['materials'][material_name]['unit']} of '{material_name}'")

    save_data()
    check_low_stock()
    return True


def create_material(material_name: str, unit: str, min_threshold: float):
    """
    Create a new raw material in the inventory.

    Args:
        material_name: Name of the material
        unit: Unit of measurement (kg, dozen, liters, etc.)
        min_threshold: Minimum quantity threshold for alerts
    """
    if material_name in bakery_data["materials"]:
        print(f"✗ Material '{material_name}' already exists.")
        return False

    bakery_data["materials"][material_name] = {
        "unit": unit,
        "min_threshold": min_threshold,
        "batches": []
    }

    print(f"✓ Material '{material_name}' created successfully.")
    save_data()
    return True


def get_material_total_quantity(material_name: str) -> float:
    """
    Calculate total quantity of a material across all batches.

    Args:
        material_name: Name of the material

    Returns:
        Total quantity available
    """
    if material_name not in bakery_data["materials"]:
        return 0.0

    total = sum(batch["quantity"] for batch in bakery_data["materials"][material_name]["batches"])
    return total


def consume_material_fifo(material_name: str, quantity_needed: float) -> Tuple[bool, str]:
    """
    Consume material using FIFO method (oldest batches first).

    Args:
        material_name: Name of the material to consume
        quantity_needed: Quantity to consume

    Returns:
        Tuple of (success: bool, message: str)
    """
    if material_name not in bakery_data["materials"]:
        return False, f"Material '{material_name}' not found in inventory."

    material = bakery_data["materials"][material_name]
    total_available = get_material_total_quantity(material_name)

    if total_available < quantity_needed:
        return False, f"Insufficient '{material_name}'. Need: {quantity_needed} {material['unit']}, Available: {total_available} {material['unit']}"

    remaining_to_consume = quantity_needed
    batches_to_remove = []

    # Consume from oldest batches first (FIFO)
    for i, batch in enumerate(material["batches"]):
        if remaining_to_consume <= 0:
            break

        if batch["quantity"] <= remaining_to_consume:
            # Consume entire batch
            remaining_to_consume -= batch["quantity"]
            batches_to_remove.append(i)
        else:
            # Consume partial batch
            batch["quantity"] -= remaining_to_consume
            remaining_to_consume = 0

    # Remove fully consumed batches (in reverse order to maintain indices)
    for i in reversed(batches_to_remove):
        material["batches"].pop(i)

    return True, f"Consumed {quantity_needed} {material['unit']} of '{material_name}'"


def view_all_materials():
    """Display all raw materials with their total quantities and batches."""
    if not bakery_data["materials"]:
        print("\n📦 No materials in inventory.")
        return

    print("\n" + "="*80)
    print("📦 RAW MATERIALS INVENTORY (FIFO)")
    print("="*80)

    for material_name, material_data in sorted(bakery_data["materials"].items()):
        total_qty = get_material_total_quantity(material_name)
        unit = material_data["unit"]
        min_threshold = material_data["min_threshold"]

        # Check if low stock
        stock_status = "⚠️  LOW STOCK" if total_qty < min_threshold else "✓"

        print(f"\n{stock_status} {material_name.upper()}")
        print(f"   Total Quantity: {total_qty} {unit}")
        print(f"   Min Threshold: {min_threshold} {unit}")
        print(f"   Batches: {len(material_data['batches'])}")

        if material_data["batches"]:
            print(f"   Batch Details:")
            for i, batch in enumerate(material_data["batches"], 1):
                print(f"      {i}. Date: {batch['purchase_date']}, "
                      f"Qty: {batch['quantity']} {unit}, "
                      f"Cost/Unit: ${batch['cost_per_unit']:.2f}")

    print("="*80)


def check_low_stock():
    """Check for materials below minimum threshold and display alerts."""
    low_stock_items = []

    for material_name, material_data in bakery_data["materials"].items():
        total_qty = get_material_total_quantity(material_name)
        if total_qty < material_data["min_threshold"]:
            low_stock_items.append({
                "name": material_name,
                "current": total_qty,
                "threshold": material_data["min_threshold"],
                "unit": material_data["unit"]
            })

    if low_stock_items:
        print("\n" + "!"*80)
        print("⚠️  LOW STOCK ALERT!")
        print("!"*80)
        for item in low_stock_items:
            print(f"   • {item['name']}: {item['current']} {item['unit']} "
                  f"(Min: {item['threshold']} {item['unit']})")
        print("!"*80)


# ============================================================================
# RECIPE MANAGEMENT
# ============================================================================

def create_recipe(product_name: str, ingredients: Dict[str, float], batch_size: int = 1):
    """
    Create a recipe for a finished product.

    Args:
        product_name: Name of the finished product
        ingredients: Dictionary of {material_name: quantity_needed}
        batch_size: Number of units produced per batch
    """
    if product_name in bakery_data["recipes"]:
        print(f"✗ Recipe for '{product_name}' already exists.")
        return False

    # Validate that all ingredients exist
    for material_name in ingredients.keys():
        if material_name not in bakery_data["materials"]:
            print(f"✗ Material '{material_name}' not found in inventory. Add it first.")
            return False

    bakery_data["recipes"][product_name] = {
        "ingredients": ingredients,
        "batch_size": batch_size
    }

    # Initialize product in products inventory if not exists
    if product_name not in bakery_data["products"]:
        bakery_data["products"][product_name] = {
            "quantity": 0,
            "price": 0.0
        }

    print(f"✓ Recipe for '{product_name}' created successfully.")
    save_data()
    return True


def view_all_recipes():
    """Display all recipes."""
    if not bakery_data["recipes"]:
        print("\n📋 No recipes available.")
        return

    print("\n" + "="*80)
    print("📋 PRODUCT RECIPES")
    print("="*80)

    for product_name, recipe_data in sorted(bakery_data["recipes"].items()):
        print(f"\n🍰 {product_name.upper()}")
        print(f"   Batch Size: {recipe_data['batch_size']} unit(s)")
        print(f"   Ingredients:")

        for material_name, quantity in recipe_data["ingredients"].items():
            unit = bakery_data["materials"].get(material_name, {}).get("unit", "units")
            available = get_material_total_quantity(material_name)
            print(f"      • {material_name}: {quantity} {unit} (Available: {available} {unit})")

    print("="*80)


# ============================================================================
# PRODUCTION TRACKING
# ============================================================================

def produce_product(product_name: str, batches: int = 1):
    """
    Produce a product by consuming raw materials according to its recipe.

    Args:
        product_name: Name of the product to produce
        batches: Number of batches to produce

    Returns:
        bool: Success status
    """
    if product_name not in bakery_data["recipes"]:
        print(f"✗ No recipe found for '{product_name}'.")
        return False

    recipe = bakery_data["recipes"][product_name]

    # Check if we have enough materials for all batches
    print(f"\n🔍 Checking material availability for {batches} batch(es) of '{product_name}'...")

    insufficient_materials = []
    for material_name, qty_per_batch in recipe["ingredients"].items():
        total_needed = qty_per_batch * batches
        available = get_material_total_quantity(material_name)
        unit = bakery_data["materials"][material_name]["unit"]

        if available < total_needed:
            insufficient_materials.append(
                f"   • {material_name}: Need {total_needed} {unit}, Have {available} {unit}"
            )

    if insufficient_materials:
        print("\n✗ Insufficient materials to produce:")
        for msg in insufficient_materials:
            print(msg)
        return False

    # Consume materials using FIFO
    print(f"\n🏭 Producing {batches} batch(es) of '{product_name}'...")
    consumed_materials = []

    for material_name, qty_per_batch in recipe["ingredients"].items():
        total_needed = qty_per_batch * batches
        success, message = consume_material_fifo(material_name, total_needed)

        if success:
            consumed_materials.append(message)
        else:
            print(f"\n✗ Production failed: {message}")
            return False

    # Update product quantity
    units_produced = recipe["batch_size"] * batches
    if product_name not in bakery_data["products"]:
        bakery_data["products"][product_name] = {"quantity": 0, "price": 0.0}

    bakery_data["products"][product_name]["quantity"] += units_produced

    print(f"\n✓ Successfully produced {units_produced} unit(s) of '{product_name}'!")
    print(f"\nMaterials consumed:")
    for msg in consumed_materials:
        print(f"   • {msg}")

    save_data()
    check_low_stock()
    return True


def view_all_products():
    """Display all finished products in inventory."""
    if not bakery_data["products"]:
        print("\n🍰 No products in inventory.")
        return

    print("\n" + "="*80)
    print("🍰 FINISHED PRODUCTS INVENTORY")
    print("="*80)

    for product_name, product_data in sorted(bakery_data["products"].items()):
        print(f"\n   {product_name.upper()}")
        print(f"      Quantity: {product_data['quantity']} unit(s)")
        print(f"      Price: ${product_data['price']:.2f} per unit")

    print("="*80)


# ============================================================================
# ADMIN INTERFACE
# ============================================================================

def admin_menu():
    """Display and handle admin menu options."""
    while True:
        clear_screen()
        print("="*80)
        print("🔧 ADMIN PANEL")
        print("="*80)
        print("\n1. Create New Material")
        print("2. Create New Recipe")
        print("3. Set Product Price")
        print("4. View All Data")
        print("5. Delete Material")
        print("6. Delete Recipe")
        print("0. Back to Main Menu")
        print("="*80)

        choice = get_valid_input("\nEnter your choice: ", str)

        if choice == "1":
            admin_create_material()
        elif choice == "2":
            admin_create_recipe()
        elif choice == "3":
            admin_set_product_price()
        elif choice == "4":
            admin_view_all_data()
        elif choice == "5":
            admin_delete_material()
        elif choice == "6":
            admin_delete_recipe()
        elif choice == "0":
            break
        else:
            print("✗ Invalid choice. Please try again.")
            pause()


def admin_create_material():
    """Admin function to create a new material."""
    clear_screen()
    print("="*80)
    print("➕ CREATE NEW MATERIAL")
    print("="*80)

    material_name = get_valid_input("\nMaterial name: ", str)
    if material_name is None:
        return

    unit = get_valid_input("Unit of measurement (kg, dozen, liters, etc.): ", str)
    if unit is None:
        return

    min_threshold = get_valid_input("Minimum threshold quantity: ", float)
    if min_threshold is None:
        return

    create_material(material_name, unit, min_threshold)
    pause()


def admin_create_recipe():
    """Admin function to create a new recipe."""
    clear_screen()
    print("="*80)
    print("📝 CREATE NEW RECIPE")
    print("="*80)

    if not bakery_data["materials"]:
        print("\n✗ No materials available. Add materials first.")
        pause()
        return

    print("\nAvailable materials:")
    for material_name in sorted(bakery_data["materials"].keys()):
        print(f"   • {material_name}")

    product_name = get_valid_input("\nProduct name: ", str)
    if product_name is None:
        return

    batch_size = get_valid_input("Batch size (units produced per batch): ", int)
    if batch_size is None:
        return

    ingredients = {}
    print("\nEnter ingredients (enter blank material name to finish):")

    while True:
        material_name = get_valid_input("\n   Material name: ", str, allow_empty=True)
        if material_name is None or material_name == "":
            break

        if material_name not in bakery_data["materials"]:
            print(f"   ✗ Material '{material_name}' not found.")
            continue

        quantity = get_valid_input(f"   Quantity of {material_name}: ", float)
        if quantity is None:
            continue

        ingredients[material_name] = quantity
        print(f"   ✓ Added {quantity} {bakery_data['materials'][material_name]['unit']} of {material_name}")

    if ingredients:
        create_recipe(product_name, ingredients, batch_size)
    else:
        print("\n✗ No ingredients added. Recipe not created.")

    pause()


def admin_set_product_price():
    """Admin function to set product price."""
    clear_screen()
    print("="*80)
    print("💰 SET PRODUCT PRICE")
    print("="*80)

    if not bakery_data["products"]:
        print("\n✗ No products available.")
        pause()
        return

    print("\nAvailable products:")
    for product_name in sorted(bakery_data["products"].keys()):
        price = bakery_data["products"][product_name]["price"]
        print(f"   • {product_name} (Current price: ${price:.2f})")

    product_name = get_valid_input("\nProduct name: ", str)
    if product_name is None:
        return

    if product_name not in bakery_data["products"]:
        print(f"✗ Product '{product_name}' not found.")
        pause()
        return

    price = get_valid_input("Price per unit: $", float)
    if price is None:
        return

    bakery_data["products"][product_name]["price"] = price
    print(f"✓ Price for '{product_name}' set to ${price:.2f}")
    save_data()
    pause()


def admin_view_all_data():
    """Admin function to view all data."""
    clear_screen()
    view_all_materials()
    input("\nPress Enter to continue...")

    clear_screen()
    view_all_recipes()
    input("\nPress Enter to continue...")

    clear_screen()
    view_all_products()
    pause()


def admin_delete_material():
    """Admin function to delete a material."""
    clear_screen()
    print("="*80)
    print("🗑️  DELETE MATERIAL")
    print("="*80)

    if not bakery_data["materials"]:
        print("\n✗ No materials to delete.")
        pause()
        return

    print("\nAvailable materials:")
    for material_name in sorted(bakery_data["materials"].keys()):
        print(f"   • {material_name}")

    material_name = get_valid_input("\nMaterial name to delete: ", str)
    if material_name is None:
        return

    if material_name not in bakery_data["materials"]:
        print(f"✗ Material '{material_name}' not found.")
        pause()
        return

    # Check if material is used in any recipes
    used_in_recipes = []
    for product_name, recipe_data in bakery_data["recipes"].items():
        if material_name in recipe_data["ingredients"]:
            used_in_recipes.append(product_name)

    if used_in_recipes:
        print(f"\n⚠️  Warning: '{material_name}' is used in the following recipes:")
        for product in used_in_recipes:
            print(f"   • {product}")
        confirm = get_valid_input("\nAre you sure you want to delete it? (yes/no): ", str)
        if confirm is None or confirm.lower() != "yes":
            print("✗ Deletion cancelled.")
            pause()
            return

    del bakery_data["materials"][material_name]
    print(f"✓ Material '{material_name}' deleted successfully.")
    save_data()
    pause()


def admin_delete_recipe():
    """Admin function to delete a recipe."""
    clear_screen()
    print("="*80)
    print("🗑️  DELETE RECIPE")
    print("="*80)

    if not bakery_data["recipes"]:
        print("\n✗ No recipes to delete.")
        pause()
        return

    print("\nAvailable recipes:")
    for product_name in sorted(bakery_data["recipes"].keys()):
        print(f"   • {product_name}")

    product_name = get_valid_input("\nRecipe name to delete: ", str)
    if product_name is None:
        return

    if product_name not in bakery_data["recipes"]:
        print(f"✗ Recipe '{product_name}' not found.")
        pause()
        return

    confirm = get_valid_input(f"Are you sure you want to delete the recipe for '{product_name}'? (yes/no): ", str)
    if confirm is None or confirm.lower() != "yes":
        print("✗ Deletion cancelled.")
        pause()
        return

    del bakery_data["recipes"][product_name]
    print(f"✓ Recipe for '{product_name}' deleted successfully.")
    save_data()
    pause()


# ============================================================================
# INVENTORY INTERFACE
# ============================================================================

def inventory_menu():
    """Display and handle inventory menu options."""
    while True:
        clear_screen()
        print("="*80)
        print("📦 INVENTORY MANAGEMENT")
        print("="*80)
        print("\n1. Add Material Batch (Purchase)")
        print("2. View All Materials")
        print("3. View All Recipes")
        print("4. Produce Product (Bake)")
        print("5. View Finished Products")
        print("6. Check Low Stock Alerts")
        print("0. Back to Main Menu")
        print("="*80)

        choice = get_valid_input("\nEnter your choice: ", str)

        if choice == "1":
            inventory_add_batch()
        elif choice == "2":
            clear_screen()
            view_all_materials()
            pause()
        elif choice == "3":
            clear_screen()
            view_all_recipes()
            pause()
        elif choice == "4":
            inventory_produce_product()
        elif choice == "5":
            clear_screen()
            view_all_products()
            pause()
        elif choice == "6":
            clear_screen()
            check_low_stock()
            pause()
        elif choice == "0":
            break
        else:
            print("✗ Invalid choice. Please try again.")
            pause()


def inventory_add_batch():
    """Inventory function to add a material batch."""
    clear_screen()
    print("="*80)
    print("📥 ADD MATERIAL BATCH (Purchase)")
    print("="*80)

    if not bakery_data["materials"]:
        print("\n✗ No materials defined. Use Admin panel to create materials first.")
        pause()
        return

    print("\nAvailable materials:")
    for material_name, material_data in sorted(bakery_data["materials"].items()):
        total = get_material_total_quantity(material_name)
        print(f"   • {material_name} (Current: {total} {material_data['unit']})")

    material_name = get_valid_input("\nMaterial name: ", str)
    if material_name is None:
        return

    if material_name not in bakery_data["materials"]:
        print(f"✗ Material '{material_name}' not found.")
        pause()
        return

    quantity = get_valid_input(f"Quantity to add ({bakery_data['materials'][material_name]['unit']}): ", float)
    if quantity is None or quantity <= 0:
        print("✗ Quantity must be positive.")
        pause()
        return

    cost_per_unit = get_valid_input("Cost per unit: $", float)
    if cost_per_unit is None or cost_per_unit < 0:
        print("✗ Cost must be non-negative.")
        pause()
        return

    purchase_date = get_valid_input(f"Purchase date (YYYY-MM-DD, or Enter for today): ", str, allow_empty=True)
    if purchase_date is None or purchase_date == "":
        purchase_date = get_current_date()

    add_material_batch(material_name, quantity, cost_per_unit, purchase_date)
    pause()


def inventory_produce_product():
    """Inventory function to produce a product."""
    clear_screen()
    print("="*80)
    print("🏭 PRODUCE PRODUCT (Bake)")
    print("="*80)

    if not bakery_data["recipes"]:
        print("\n✗ No recipes available. Use Admin panel to create recipes first.")
        pause()
        return

    print("\nAvailable recipes:")
    for product_name, recipe_data in sorted(bakery_data["recipes"].items()):
        current_qty = bakery_data["products"].get(product_name, {}).get("quantity", 0)
        print(f"   • {product_name} (Current stock: {current_qty} units, Batch size: {recipe_data['batch_size']})")

    product_name = get_valid_input("\nProduct name to produce: ", str)
    if product_name is None:
        return

    if product_name not in bakery_data["recipes"]:
        print(f"✗ Recipe for '{product_name}' not found.")
        pause()
        return

    batches = get_valid_input("Number of batches to produce: ", int)
    if batches is None or batches <= 0:
        print("✗ Number of batches must be positive.")
        pause()
        return

    produce_product(product_name, batches)
    pause()


# ============================================================================
# POS (Point of Sale) INTERFACE
# ============================================================================

def pos_menu():
    """Display and handle POS menu options."""
    while True:
        clear_screen()
        print("="*80)
        print("💰 POINT OF SALE (POS)")
        print("="*80)
        print("\n1. Sell Product")
        print("2. View Available Products")
        print("3. View Sales Summary")
        print("4. Delete Sale Record")
        print("5. Clear All Sales History")
        print("0. Back to Main Menu")
        print("="*80)

        choice = get_valid_input("\nEnter your choice: ", str)

        if choice == "1":
            pos_sell_product()
        elif choice == "2":
            clear_screen()
            view_all_products()
            pause()
        elif choice == "3":
            pos_sales_summary()
        elif choice == "4":
            pos_delete_sale()
        elif choice == "5":
            pos_clear_sales_history()
        elif choice == "0":
            break
        else:
            print("✗ Invalid choice. Please try again.")
            pause()


def pos_sell_product():
    """POS function to sell a product."""
    clear_screen()
    print("="*80)
    print("🛒 SELL PRODUCT")
    print("="*80)

    if not bakery_data["products"]:
        print("\n✗ No products available to sell.")
        pause()
        return

    # Show available products with stock
    print("\nAvailable products:")
    available_products = []
    for product_name, product_data in sorted(bakery_data["products"].items()):
        if product_data["quantity"] > 0:
            print(f"   • {product_name}: {product_data['quantity']} units @ ${product_data['price']:.2f}")
            available_products.append(product_name)
        else:
            print(f"   • {product_name}: OUT OF STOCK")

    if not available_products:
        print("\n✗ No products in stock.")
        pause()
        return

    product_name = get_valid_input("\nProduct name to sell: ", str)
    if product_name is None:
        return

    if product_name not in bakery_data["products"]:
        print(f"✗ Product '{product_name}' not found.")
        pause()
        return

    product_data = bakery_data["products"][product_name]

    if product_data["quantity"] <= 0:
        print(f"✗ '{product_name}' is out of stock.")
        pause()
        return

    quantity = get_valid_input(f"Quantity to sell (Available: {product_data['quantity']}): ", int)
    if quantity is None or quantity <= 0:
        print("✗ Quantity must be positive.")
        pause()
        return

    if quantity > product_data["quantity"]:
        print(f"✗ Insufficient stock. Only {product_data['quantity']} units available.")
        pause()
        return

    # Calculate total
    total_price = quantity * product_data["price"]

    print(f"\n{'─'*50}")
    print(f"Product: {product_name}")
    print(f"Quantity: {quantity} units")
    print(f"Price per unit: ${product_data['price']:.2f}")
    print(f"{'─'*50}")
    print(f"TOTAL: ${total_price:.2f}")
    print(f"{'─'*50}")

    confirm = get_valid_input("\nConfirm sale? (yes/no): ", str)
    if confirm is None or confirm.lower() != "yes":
        print("✗ Sale cancelled.")
        pause()
        return

    # Process sale
    product_data["quantity"] -= quantity

    # Record sale in data (optional: you can add a sales log)
    if "sales" not in bakery_data:
        bakery_data["sales"] = []

    sale_record = {
        "product": product_name,
        "quantity": quantity,
        "price_per_unit": product_data["price"],
        "total": total_price,
        "date": get_current_date()
    }
    bakery_data["sales"].append(sale_record)

    print(f"\n✓ Sale completed! Total: ${total_price:.2f}")
    print(f"   Remaining stock: {product_data['quantity']} units")

    save_data()
    pause()


def pos_sales_summary():
    """POS function to view sales summary."""
    clear_screen()
    print("="*80)
    print("📊 SALES SUMMARY")
    print("="*80)

    if "sales" not in bakery_data or not bakery_data["sales"]:
        print("\n✗ No sales recorded yet.")
        pause()
        return

    total_revenue = 0
    product_sales = {}

    print(f"\n{'Date':<12} {'Product':<20} {'Qty':<8} {'Price/Unit':<12} {'Total':<10}")
    print("─"*80)

    for sale in bakery_data["sales"]:
        print(f"{sale['date']:<12} {sale['product']:<20} {sale['quantity']:<8} "
              f"${sale['price_per_unit']:<11.2f} ${sale['total']:<9.2f}")

        total_revenue += sale["total"]

        if sale["product"] not in product_sales:
            product_sales[sale["product"]] = {"quantity": 0, "revenue": 0}

        product_sales[sale["product"]]["quantity"] += sale["quantity"]
        product_sales[sale["product"]]["revenue"] += sale["total"]

    print("─"*80)
    print(f"\n💰 Total Revenue: ${total_revenue:.2f}")

    print("\n📈 Sales by Product:")
    for product, data in sorted(product_sales.items()):
        print(f"   • {product}: {data['quantity']} units, ${data['revenue']:.2f}")

    pause()


def pos_delete_sale():
    """POS function to delete a specific sale record."""
    clear_screen()
    print("="*80)
    print("🗑️  DELETE SALE RECORD")
    print("="*80)

    if "sales" not in bakery_data or not bakery_data["sales"]:
        print("\n✗ No sales records to delete.")
        pause()
        return

    # Display all sales with indices
    print("\nSales Records:")
    print(f"\n{'#':<5} {'Date':<12} {'Product':<20} {'Qty':<8} {'Price/Unit':<12} {'Total':<10}")
    print("─"*80)

    for idx, sale in enumerate(bakery_data["sales"], 1):
        print(f"{idx:<5} {sale['date']:<12} {sale['product']:<20} {sale['quantity']:<8} "
              f"${sale['price_per_unit']:<11.2f} ${sale['total']:<9.2f}")

    print("─"*80)
    print(f"\nTotal records: {len(bakery_data['sales'])}")

    # Get sale index to delete
    sale_index = get_valid_input("\nEnter sale record number to delete (or 0 to cancel): ", int)
    if sale_index is None or sale_index == 0:
        print("✗ Deletion cancelled.")
        pause()
        return

    if sale_index < 1 or sale_index > len(bakery_data["sales"]):
        print(f"✗ Invalid record number. Please enter a number between 1 and {len(bakery_data['sales'])}.")
        pause()
        return

    # Get the sale to delete (adjust index to 0-based)
    sale_to_delete = bakery_data["sales"][sale_index - 1]

    # Show confirmation
    print(f"\n⚠️  You are about to delete the following sale:")
    print(f"   Date: {sale_to_delete['date']}")
    print(f"   Product: {sale_to_delete['product']}")
    print(f"   Quantity: {sale_to_delete['quantity']} units")
    print(f"   Total: ${sale_to_delete['total']:.2f}")

    confirm = get_valid_input("\nAre you sure you want to delete this sale? (yes/no): ", str)
    if confirm is None or confirm.lower() != "yes":
        print("✗ Deletion cancelled.")
        pause()
        return

    # Delete the sale
    deleted_sale = bakery_data["sales"].pop(sale_index - 1)

    print(f"\n✓ Sale record deleted successfully!")
    print(f"   Deleted: {deleted_sale['product']} - ${deleted_sale['total']:.2f} on {deleted_sale['date']}")

    save_data()
    pause()


def pos_clear_sales_history():
    """POS function to clear all sales history."""
    clear_screen()
    print("="*80)
    print("🗑️  CLEAR ALL SALES HISTORY")
    print("="*80)

    if "sales" not in bakery_data or not bakery_data["sales"]:
        print("\n✗ No sales records to clear.")
        pause()
        return

    # Calculate total sales statistics before clearing
    total_records = len(bakery_data["sales"])
    total_revenue = sum(sale["total"] for sale in bakery_data["sales"])

    print(f"\n⚠️  WARNING: You are about to delete ALL sales history!")
    print(f"\n   Total sales records: {total_records}")
    print(f"   Total revenue: ${total_revenue:.2f}")
    print(f"\n   This action CANNOT be undone!")

    confirm = get_valid_input("\nAre you sure you want to clear all sales history? (yes/no): ", str)
    if confirm is None or confirm.lower() != "yes":
        print("✗ Operation cancelled.")
        pause()
        return

    # Second confirmation for safety
    confirm2 = get_valid_input("Type 'DELETE ALL' to confirm: ", str)
    if confirm2 is None or confirm2 != "DELETE ALL":
        print("✗ Operation cancelled. Sales history preserved.")
        pause()
        return

    # Clear all sales
    bakery_data["sales"] = []

    print(f"\n✓ All sales history cleared successfully!")
    print(f"   Deleted {total_records} sales records totaling ${total_revenue:.2f}")

    save_data()
    pause()


# ============================================================================
# MAIN MENU
# ============================================================================

def main_menu():
    """Display and handle main menu options."""
    while True:
        clear_screen()
        print("="*80)
        print("🥐 BAKERY INVENTORY MANAGEMENT SYSTEM 🥐")
        print("="*80)
        print("\n1. 🔧 Admin Panel")
        print("2. 📦 Inventory Management")
        print("3. 💰 Point of Sale (POS)")
        print("4. 💾 Save Data")
        print("5. 🔄 Reload Data")
        print("0. 🚪 Exit")
        print("="*80)

        choice = get_valid_input("\nEnter your choice: ", str)

        if choice == "1":
            admin_menu()
        elif choice == "2":
            inventory_menu()
        elif choice == "3":
            pos_menu()
        elif choice == "4":
            save_data()
            pause()
        elif choice == "5":
            load_data()
            pause()
        elif choice == "0":
            print("\n👋 Thank you for using Bakery Inventory Management System!")
            save_data()
            break
        else:
            print("✗ Invalid choice. Please try again.")
            pause()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point of the application."""
    try:
        clear_screen()
        print("="*80)
        print("🥐 BAKERY INVENTORY MANAGEMENT SYSTEM 🥐")
        print("="*80)
        print("\nInitializing...")

        # Load data from file
        load_data()

        # Check for low stock on startup
        check_low_stock()

        input("\nPress Enter to continue to main menu...")

        # Run main menu
        main_menu()

    except KeyboardInterrupt:
        print("\n\n✗ Program interrupted by user.")
        save_data()
    except Exception as e:
        print(f"\n✗ An unexpected error occurred: {e}")
        save_data()


if __name__ == "__main__":
    main()
