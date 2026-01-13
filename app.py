from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'bakery_secret_key_change_in_production'

# Global data structure
bakery_data = {
    "materials": {},
    "recipes": {},
    "products": {},
    "sales": []
}

DATA_FILE = "bakery_data.json"

# ==================== Data Persistence ====================

def load_data():
    """Load bakery data from JSON file"""
    global bakery_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                bakery_data = json.load(f)
            return True
        except (json.JSONDecodeError, IOError):
            return False
    return False

def save_data():
    """Save bakery data to JSON file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(bakery_data, f, indent=2)
        return True
    except IOError:
        return False

# ==================== Utility Functions ====================

def get_low_stock_alerts():
    """Get list of materials that are below minimum quantity"""
    alerts = []
    for material_name, material in bakery_data["materials"].items():
        total_qty = sum(batch['quantity'] for batch in material['batches'])
        if total_qty < material['min_quantity']:
            alerts.append({
                'name': material_name,
                'current': total_qty,
                'minimum': material['min_quantity'],
                'unit': material['unit']
            })
    return alerts

def calculate_recipe_availability(recipe_name):
    """Calculate how many batches can be made from available materials"""
    if recipe_name not in bakery_data["recipes"]:
        return 0

    recipe = bakery_data["recipes"][recipe_name]
    max_batches = float('inf')

    for ingredient in recipe['ingredients']:
        material_name = ingredient['material']
        required_qty = ingredient['quantity']

        if material_name not in bakery_data["materials"]:
            return 0

        material = bakery_data["materials"][material_name]
        total_available = sum(batch['quantity'] for batch in material['batches'])

        possible_batches = int(total_available / required_qty)
        max_batches = min(max_batches, possible_batches)

    return max_batches if max_batches != float('inf') else 0

# ==================== Material Management ====================

def create_material(name, unit, min_quantity):
    """Create a new raw material"""
    if name in bakery_data["materials"]:
        return False, "Material already exists"

    bakery_data["materials"][name] = {
        "unit": unit,
        "min_quantity": min_quantity,
        "batches": []
    }
    save_data()
    return True, "Material created successfully"

def add_material_batch(material_name, quantity, cost_per_unit, purchase_date=None):
    """Add a batch of material to inventory"""
    if material_name not in bakery_data["materials"]:
        return False, "Material does not exist"

    if purchase_date is None:
        purchase_date = datetime.now().strftime("%Y-%m-%d")

    batch = {
        "quantity": quantity,
        "cost_per_unit": cost_per_unit,
        "purchase_date": purchase_date
    }

    bakery_data["materials"][material_name]["batches"].append(batch)
    save_data()
    return True, "Batch added successfully"

def consume_material_fifo(material_name, quantity_needed):
    """Consume material using FIFO method"""
    if material_name not in bakery_data["materials"]:
        return False, "Material not found"

    material = bakery_data["materials"][material_name]
    total_available = sum(batch['quantity'] for batch in material['batches'])

    if total_available < quantity_needed:
        return False, "Insufficient material"

    remaining_needed = quantity_needed
    batches_to_remove = []

    for i, batch in enumerate(material['batches']):
        if remaining_needed <= 0:
            break

        if batch['quantity'] <= remaining_needed:
            remaining_needed -= batch['quantity']
            batches_to_remove.append(i)
        else:
            batch['quantity'] -= remaining_needed
            remaining_needed = 0

    for i in reversed(batches_to_remove):
        material['batches'].pop(i)

    return True, "Material consumed"

def delete_material(material_name):
    """Delete a material from inventory"""
    if material_name not in bakery_data["materials"]:
        return False, "Material not found"

    # Check if material is used in any recipes
    used_in_recipes = []
    for recipe_name, recipe_data in bakery_data["recipes"].items():
        for ingredient in recipe_data['ingredients']:
            if ingredient['material'] == material_name:
                used_in_recipes.append(recipe_name)
                break

    if used_in_recipes:
        recipes_list = ", ".join(used_in_recipes)
        return False, f"Cannot delete material. Used in recipes: {recipes_list}"

    # Delete the material
    del bakery_data["materials"][material_name]
    save_data()
    return True, f"Material '{material_name}' deleted successfully"

# ==================== Recipe Management ====================

def create_recipe(name, ingredients, batch_size):
    """Create a new recipe"""
    if name in bakery_data["recipes"]:
        return False, "Recipe already exists"

    # Validate all materials exist
    for ingredient in ingredients:
        if ingredient['material'] not in bakery_data["materials"]:
            return False, f"Material '{ingredient['material']}' does not exist"

    bakery_data["recipes"][name] = {
        "ingredients": ingredients,
        "batch_size": batch_size
    }
    save_data()
    return True, "Recipe created successfully"

# ==================== Production ====================

def produce_product(recipe_name, batches_to_make):
    """Produce products using a recipe"""
    if recipe_name not in bakery_data["recipes"]:
        return False, "Recipe not found"

    recipe = bakery_data["recipes"][recipe_name]

    # Check if we have enough materials
    for ingredient in recipe['ingredients']:
        material_name = ingredient['material']
        required_qty = ingredient['quantity'] * batches_to_make

        if material_name not in bakery_data["materials"]:
            return False, f"Material '{material_name}' not found"

        material = bakery_data["materials"][material_name]
        total_available = sum(batch['quantity'] for batch in material['batches'])

        if total_available < required_qty:
            return False, f"Insufficient '{material_name}'. Need {required_qty}, have {total_available}"

    # Consume materials using FIFO
    for ingredient in recipe['ingredients']:
        material_name = ingredient['material']
        required_qty = ingredient['quantity'] * batches_to_make
        success, msg = consume_material_fifo(material_name, required_qty)
        if not success:
            return False, msg

    # Add to finished products
    product_name = recipe_name
    total_quantity = recipe['batch_size'] * batches_to_make

    if product_name not in bakery_data["products"]:
        bakery_data["products"][product_name] = {
            "quantity": 0,
            "price": 0
        }

    bakery_data["products"][product_name]["quantity"] += total_quantity
    save_data()

    return True, f"Produced {total_quantity} units of {product_name}"

def set_product_price(product_name, price):
    """Set the selling price for a product"""
    if product_name not in bakery_data["products"]:
        return False, "Product not found"

    bakery_data["products"][product_name]["price"] = price
    save_data()
    return True, "Price updated successfully"

# ==================== Point of Sale ====================

def sell_product(product_name, quantity):
    """Sell a product"""
    if product_name not in bakery_data["products"]:
        return False, "Product not found"

    product = bakery_data["products"][product_name]

    if product["quantity"] < quantity:
        return False, f"Insufficient stock. Available: {product['quantity']}"

    if product["price"] <= 0:
        return False, "Product price not set"

    total_amount = product["price"] * quantity

    sale = {
        "product": product_name,
        "quantity": quantity,
        "price": product["price"],
        "total": total_amount,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    product["quantity"] -= quantity
    bakery_data["sales"].append(sale)
    save_data()

    return True, f"Sale completed. Total: ${total_amount:.2f}"

def get_sales_summary():
    """Get sales summary statistics"""
    if not bakery_data["sales"]:
        return {"total_revenue": 0, "total_sales": 0, "products": {}}

    total_revenue = sum(sale["total"] for sale in bakery_data["sales"])
    total_sales = len(bakery_data["sales"])

    products = defaultdict(lambda: {"quantity": 0, "revenue": 0})

    for sale in bakery_data["sales"]:
        product_name = sale["product"]
        products[product_name]["quantity"] += sale["quantity"]
        products[product_name]["revenue"] += sale["total"]

    return {
        "total_revenue": total_revenue,
        "total_sales": total_sales,
        "products": dict(products)
    }

def delete_sale(index):
    """Delete a specific sale by index"""
    if index < 0 or index >= len(bakery_data["sales"]):
        return False, "Invalid sale index"

    deleted_sale = bakery_data["sales"].pop(index)
    save_data()
    return True, f"Sale deleted: {deleted_sale['product']} - ${deleted_sale['total']:.2f}"

def clear_all_sales():
    """Clear all sales history"""
    if not bakery_data["sales"]:
        return False, "No sales history to clear"

    count = len(bakery_data["sales"])
    total = sum(sale["total"] for sale in bakery_data["sales"])
    bakery_data["sales"] = []
    save_data()
    return True, f"Cleared {count} sales records totaling ${total:.2f}"

# ==================== Routes ====================

@app.route('/')
def index():
    """Home page"""
    alerts = get_low_stock_alerts()
    sales_summary = get_sales_summary()
    return render_template('index.html',
                         alerts=alerts,
                         sales_summary=sales_summary,
                         materials_count=len(bakery_data["materials"]),
                         recipes_count=len(bakery_data["recipes"]),
                         products_count=len(bakery_data["products"]))

# Material routes
@app.route('/materials')
def materials():
    """View all materials"""
    materials_with_total = {}
    for name, material in bakery_data["materials"].items():
        total_qty = sum(batch['quantity'] for batch in material['batches'])
        materials_with_total[name] = {
            **material,
            'total_quantity': total_qty
        }
    return render_template('materials.html', materials=materials_with_total)

@app.route('/materials/add', methods=['GET', 'POST'])
def add_material():
    """Add a new material"""
    if request.method == 'POST':
        name = request.form.get('name')
        unit = request.form.get('unit')
        min_quantity = float(request.form.get('min_quantity', 0))

        success, message = create_material(name, unit, min_quantity)
        if success:
            flash(message, 'success')
            return redirect(url_for('materials'))
        else:
            flash(message, 'error')

    return render_template('add_material.html')

@app.route('/materials/add_batch/<material_name>', methods=['GET', 'POST'])
def add_batch(material_name):
    """Add a batch to existing material"""
    if material_name not in bakery_data["materials"]:
        flash('Material not found', 'error')
        return redirect(url_for('materials'))

    if request.method == 'POST':
        quantity = float(request.form.get('quantity'))
        cost_per_unit = float(request.form.get('cost_per_unit'))
        purchase_date = request.form.get('purchase_date')

        success, message = add_material_batch(material_name, quantity, cost_per_unit, purchase_date)
        flash(message, 'success' if success else 'error')
        return redirect(url_for('materials'))

    material = bakery_data["materials"][material_name]
    return render_template('add_batch.html', material_name=material_name, material=material)

@app.route('/materials/delete/<material_name>', methods=['POST'])
def delete_material_route(material_name):
    """Delete a material"""
    success, message = delete_material(material_name)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('materials'))

# Recipe routes
@app.route('/recipes')
def recipes():
    """View all recipes"""
    recipes_with_availability = {}
    for name, recipe in bakery_data["recipes"].items():
        availability = calculate_recipe_availability(name)
        recipes_with_availability[name] = {
            **recipe,
            'can_make': availability
        }
    return render_template('recipes.html', recipes=recipes_with_availability)

@app.route('/recipes/add', methods=['GET', 'POST'])
def add_recipe():
    """Add a new recipe"""
    if request.method == 'POST':
        name = request.form.get('name')
        batch_size = int(request.form.get('batch_size'))

        # Parse ingredients
        ingredients = []
        ingredient_count = int(request.form.get('ingredient_count', 0))

        for i in range(ingredient_count):
            material = request.form.get(f'ingredient_material_{i}')
            quantity = float(request.form.get(f'ingredient_quantity_{i}'))
            if material and quantity:
                ingredients.append({
                    'material': material,
                    'quantity': quantity
                })

        if not ingredients:
            flash('At least one ingredient is required', 'error')
            return render_template('add_recipe.html', materials=bakery_data["materials"])

        success, message = create_recipe(name, ingredients, batch_size)
        flash(message, 'success' if success else 'error')
        if success:
            return redirect(url_for('recipes'))

    return render_template('add_recipe.html', materials=bakery_data["materials"])

# Production routes
@app.route('/production')
def production():
    """View production page"""
    return render_template('production.html', recipes=bakery_data["recipes"])

@app.route('/production/produce/<recipe_name>', methods=['POST'])
def produce(recipe_name):
    """Produce products from a recipe"""
    batches = int(request.form.get('batches', 1))
    success, message = produce_product(recipe_name, batches)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('production'))

# Product routes
@app.route('/products')
def products():
    """View all products"""
    return render_template('products.html', products=bakery_data["products"])

@app.route('/products/set_price/<product_name>', methods=['POST'])
def set_price(product_name):
    """Set product price"""
    price = float(request.form.get('price'))
    success, message = set_product_price(product_name, price)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('products'))

# Sales routes
@app.route('/sales')
def sales():
    """Point of sale page"""
    return render_template('sales.html', products=bakery_data["products"])

@app.route('/sales/sell/<product_name>', methods=['POST'])
def sell(product_name):
    """Sell a product"""
    quantity = int(request.form.get('quantity', 1))
    success, message = sell_product(product_name, quantity)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('sales'))

@app.route('/sales/history')
def sales_history():
    """View sales history"""
    summary = get_sales_summary()
    recent_sales = sorted(bakery_data["sales"], key=lambda x: x['date'], reverse=True)[:50]
    return render_template('sales_history.html', sales=recent_sales, summary=summary)

@app.route('/sales/delete/<int:index>', methods=['POST'])
def delete_sale_record(index):
    """Delete a specific sale record"""
    success, message = delete_sale(index)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('sales_history'))

@app.route('/sales/clear', methods=['POST'])
def clear_sales():
    """Clear all sales history"""
    success, message = clear_all_sales()
    flash(message, 'success' if success else 'error')
    return redirect(url_for('sales_history'))

# API routes for AJAX
@app.route('/api/alerts')
def api_alerts():
    """Get low stock alerts as JSON"""
    alerts = get_low_stock_alerts()
    return jsonify(alerts)

# Initialize data on startup
load_data()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
