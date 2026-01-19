from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import os
from datetime import datetime, date
from collections import defaultdict
from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from models import db, User, Material, MaterialBatch, Recipe, RecipeIngredient, Product, Sale
from google.cloud import secretmanager

app = Flask(__name__)

# ==================== Secret Management ====================

def get_secret(secret_name, project_id=None, fallback_env_var=None):
    """
    Fetch a secret from Google Cloud Secret Manager.
    Falls back to environment variable if Secret Manager is unavailable (for local dev).

    Args:
        secret_name: Name of the secret in Secret Manager
        project_id: GCP project ID (defaults to GCP_PROJECT_ID env var)
        fallback_env_var: Environment variable to use as fallback (defaults to secret_name)

    Returns:
        Secret value as string, or None if not found
    """
    # Try to get from Secret Manager first
    try:
        if project_id is None:
            project_id = os.environ.get('GCP_PROJECT_ID')

        if project_id:
            client = secretmanager.SecretManagerServiceClient()
            secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": secret_path})
            secret_value = response.payload.data.decode('UTF-8')
            print(f"Successfully fetched secret '{secret_name}' from Secret Manager")
            return secret_value
    except Exception as e:
        print(f"Could not fetch secret '{secret_name}' from Secret Manager: {e}")
        print(f"Falling back to environment variable")

    # Fallback to environment variable
    env_var = fallback_env_var if fallback_env_var else secret_name
    return os.environ.get(env_var)

# Configuration
# Fetch secrets from Google Cloud Secret Manager (with fallback to env vars)
app.secret_key = get_secret('SECRET_KEY')

# Google OAuth Configuration
app.config['GOOGLE_CLIENT_ID'] = get_secret('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = get_secret('GOOGLE_CLIENT_SECRET')
app.config['GOOGLE_DISCOVERY_URL'] = 'https://accounts.google.com/.well-known/openid-configuration'

# Database configuration
database_url = get_secret('DATABASE_URL')
if database_url:
    # Handle PostgreSQL URL (some platforms use postgres:// instead of postgresql://)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Fallback to SQLite for local development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bakery.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Initialize OAuth
oauth = OAuth(app)

# Check if OAuth credentials are configured
if not app.config['GOOGLE_CLIENT_ID'] or not app.config['GOOGLE_CLIENT_SECRET']:
    print("WARNING: Google OAuth credentials are not configured!")
    print("Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file")
    print("See OAUTH_SETUP.md for instructions")
    oauth_configured = False
else:
    oauth_configured = True

google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url=app.config['GOOGLE_DISCOVERY_URL'],
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))

# Database initialization flag
_db_initialized = False

def ensure_db_initialized():
    """Ensure database tables are created (lazy initialization)"""
    global _db_initialized
    if not _db_initialized:
        try:
            db.create_all()
            _db_initialized = True
            print("Database tables created successfully")
        except Exception as e:
            print(f"Warning: Could not create database tables: {e}")
            raise

@app.before_request
def initialize_database():
    """Initialize database before first request"""
    if request.endpoint and request.endpoint != 'health_check':
        ensure_db_initialized()
# Create tables if they don't exist
def init_db():
    """Initialize database tables"""
    try:
        with app.app_context():
            db.create_all()
            print("Database tables created successfully")
    except Exception as e:
        print(f"Warning: Could not create database tables on startup: {e}")
        print("Tables will be created on first request if needed")

# Don't initialize database on startup - it blocks container startup
# Database will be initialized on first health check or request
init_db()

# ==================== Utility Functions ====================

def get_low_stock_alerts():
    """Get list of materials that are below minimum quantity"""
    alerts = []
    materials = Material.query.all()

    for material in materials:
        total_qty = material.get_total_quantity()
        if total_qty < material.min_quantity:
            alerts.append({
                'name': material.name,
                'current': total_qty,
                'minimum': material.min_quantity,
                'unit': material.unit
            })

    return alerts

def calculate_recipe_availability(recipe_name):
    """Calculate how many batches can be made from available materials"""
    recipe = Recipe.query.filter_by(name=recipe_name).first()
    if not recipe:
        return 0

    max_batches = float('inf')

    for ingredient in recipe.ingredients:
        material = ingredient.material
        required_qty = ingredient.quantity
        total_available = material.get_total_quantity()

        if total_available < required_qty:
            return 0

        possible_batches = int(total_available / required_qty)
        max_batches = min(max_batches, possible_batches)

    return max_batches if max_batches != float('inf') else 0

# ==================== Material Management ====================

def create_material(name, unit, min_quantity):
    """Create a new raw material"""
    existing = Material.query.filter_by(name=name).first()
    if existing:
        return False, "Material already exists"

    material = Material(
        name=name,
        unit=unit,
        min_quantity=min_quantity
    )

    db.session.add(material)
    db.session.commit()

    return True, "Material created successfully"

def add_material_batch(material_name, quantity, cost_per_unit, purchase_date=None):
    """Add a batch of material to inventory"""
    material = Material.query.filter_by(name=material_name).first()
    if not material:
        return False, "Material does not exist"

    if purchase_date is None:
        purchase_date = date.today()
    elif isinstance(purchase_date, str):
        purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d").date()

    batch = MaterialBatch(
        material_id=material.id,
        quantity=quantity,
        cost_per_unit=cost_per_unit,
        purchase_date=purchase_date
    )

    db.session.add(batch)
    db.session.commit()

    return True, "Batch added successfully"

def consume_material_fifo(material_name, quantity_needed):
    """Consume material using FIFO method"""
    material = Material.query.filter_by(name=material_name).first()
    if not material:
        return False, "Material not found"

    total_available = material.get_total_quantity()

    if total_available < quantity_needed:
        return False, "Insufficient material"

    remaining_needed = quantity_needed
    batches = MaterialBatch.query.filter_by(material_id=material.id)\
        .order_by(MaterialBatch.purchase_date).all()

    for batch in batches:
        if remaining_needed <= 0:
            break

        if batch.quantity <= remaining_needed:
            remaining_needed -= batch.quantity
            db.session.delete(batch)
        else:
            batch.quantity -= remaining_needed
            remaining_needed = 0

    db.session.commit()
    return True, "Material consumed"

def delete_material(material_name):
    """Delete a material from inventory"""
    material = Material.query.filter_by(name=material_name).first()
    if not material:
        return False, "Material not found"

    # Check if material is used in any recipes
    used_in_recipes = RecipeIngredient.query.filter_by(material_id=material.id).all()

    if used_in_recipes:
        recipe_names = [ing.recipe.name for ing in used_in_recipes]
        recipes_list = ", ".join(set(recipe_names))
        return False, f"Cannot delete material. Used in recipes: {recipes_list}"

    # Delete the material (batches will be cascade deleted)
    db.session.delete(material)
    db.session.commit()

    return True, f"Material '{material_name}' deleted successfully"

# ==================== Recipe Management ====================

def create_recipe(name, ingredients, batch_size):
    """Create a new recipe"""
    existing = Recipe.query.filter_by(name=name).first()
    if existing:
        return False, "Recipe already exists"

    recipe = Recipe(
        name=name,
        batch_size=batch_size
    )

    db.session.add(recipe)
    db.session.flush()  # Get the recipe ID

    # Add ingredients
    for ingredient_data in ingredients:
        material = Material.query.filter_by(name=ingredient_data['material']).first()
        if not material:
            db.session.rollback()
            return False, f"Material '{ingredient_data['material']}' does not exist"

        ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            material_id=material.id,
            quantity=ingredient_data['quantity']
        )
        db.session.add(ingredient)

    db.session.commit()
    return True, "Recipe created successfully"

# ==================== Production ====================

def produce_product(recipe_name, batches_to_make):
    """Produce products using a recipe"""
    recipe = Recipe.query.filter_by(name=recipe_name).first()
    if not recipe:
        return False, "Recipe not found"

    # Check if we have enough materials
    for ingredient in recipe.ingredients:
        material = ingredient.material
        required_qty = ingredient.quantity * batches_to_make
        total_available = material.get_total_quantity()

        if total_available < required_qty:
            return False, f"Insufficient '{material.name}'. Need {required_qty}, have {total_available}"

    # Consume materials using FIFO
    for ingredient in recipe.ingredients:
        required_qty = ingredient.quantity * batches_to_make
        success, msg = consume_material_fifo(ingredient.material.name, required_qty)
        if not success:
            db.session.rollback()
            return False, msg

    # Add to finished products
    product_name = recipe_name
    total_quantity = recipe.batch_size * batches_to_make

    product = Product.query.filter_by(name=product_name).first()
    if not product:
        product = Product(
            name=product_name,
            quantity=0,
            price=0
        )
        db.session.add(product)

    product.quantity += total_quantity
    db.session.commit()

    return True, f"Produced {total_quantity} units of {product_name}"

def set_product_price(product_name, price):
    """Set the selling price for a product"""
    product = Product.query.filter_by(name=product_name).first()
    if not product:
        return False, "Product not found"

    product.price = price
    db.session.commit()

    return True, "Price updated successfully"

# ==================== Point of Sale ====================

def sell_product(product_name, quantity):
    """Sell a product"""
    product = Product.query.filter_by(name=product_name).first()
    if not product:
        return False, "Product not found"

    if product.quantity < quantity:
        return False, f"Insufficient stock. Available: {product.quantity}"

    if product.price <= 0:
        return False, "Product price not set"

    total_amount = product.price * quantity

    sale = Sale(
        product_id=product.id,
        product_name=product.name,
        quantity=quantity,
        price=product.price,
        total=total_amount,
        date=datetime.now()
    )

    product.quantity -= quantity

    db.session.add(sale)
    db.session.commit()

    return True, f"Sale completed. Total: ${total_amount:.2f}"

def get_sales_summary():
    """Get sales summary statistics"""
    sales = Sale.query.all()

    if not sales:
        return {"total_revenue": 0, "total_sales": 0, "products": {}}

    total_revenue = sum(sale.total for sale in sales)
    total_sales = len(sales)

    products = defaultdict(lambda: {"quantity": 0, "revenue": 0})

    for sale in sales:
        products[sale.product_name]["quantity"] += sale.quantity
        products[sale.product_name]["revenue"] += sale.total

    return {
        "total_revenue": total_revenue,
        "total_sales": total_sales,
        "products": dict(products)
    }

def delete_sale(sale_id):
    """Delete a specific sale by ID"""
    sale = Sale.query.get(sale_id)
    if not sale:
        return False, "Sale not found"

    deleted_info = f"Sale deleted: {sale.product_name} - ${sale.total:.2f}"

    db.session.delete(sale)
    db.session.commit()

    return True, deleted_info

def clear_all_sales():
    """Clear all sales history"""
    sales = Sale.query.all()

    if not sales:
        return False, "No sales history to clear"

    count = len(sales)
    total = sum(sale.total for sale in sales)

    Sale.query.delete()
    db.session.commit()

    return True, f"Cleared {count} sales records totaling ${total:.2f}"

# ==================== Authentication Routes ====================

@app.route('/login')
def login():
    """Display login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html', oauth_enabled=oauth_configured)

@app.route('/login/google')
def google_login():
    """Initiate Google OAuth login"""
    # Check if OAuth is configured
    if not oauth_configured:
        flash('Google OAuth is not configured. Please contact the administrator.', 'error')
        flash('See OAUTH_SETUP.md for instructions on setting up Google OAuth.', 'info')
        return redirect(url_for('login'))

    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/callback')
def google_callback():
    """Handle Google OAuth callback"""
    if not oauth_configured or google is None:
        flash('Google OAuth is not configured. Please contact the administrator.', 'error')
        return redirect(url_for('login'))

    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        if user_info:
            # Check if user exists
            user = User.query.filter_by(google_id=user_info['sub']).first()

            if not user:
                # Create new user
                user = User(
                    google_id=user_info['sub'],
                    email=user_info['email'],
                    name=user_info.get('name'),
                    picture=user_info.get('picture')
                )
                db.session.add(user)
            else:
                # Update existing user info
                user.name = user_info.get('name')
                user.picture = user_info.get('picture')
                user.last_login = datetime.utcnow()

            db.session.commit()
            login_user(user)
            flash(f'Welcome, {user.name}!', 'success')

            # Redirect to originally requested page or home
            next_page = session.get('next')
            if next_page:
                session.pop('next')
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Failed to get user information from Google.', 'error')
            return redirect(url_for('login'))

    except Exception as e:
        flash(f'Authentication error: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    """Log out the current user"""
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

# ==================== Routes ====================

@app.route('/health')
def health_check():
    """Health check endpoint for Cloud Run (no authentication required)"""
    # Always return 200 OK so Cloud Run considers the container healthy
    # Database connection is optional at startup
    db_status = "not_connected"
    try:
        # Initialize database tables if needed
        ensure_db_initialized()
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        print(f"Health check failed: {e}")
        # Return 200 even if DB is not ready yet to allow container to start
        # This gives Cloud SQL proxy time to establish connection
        return jsonify({"status": "starting", "message": "Database initializing"}), 200

@app.route('/')
@login_required
def index():
    """Home page"""
    alerts = get_low_stock_alerts()
    sales_summary = get_sales_summary()

    materials_count = Material.query.count()
    recipes_count = Recipe.query.count()
    products_count = Product.query.count()

    return render_template('index.html',
                         alerts=alerts,
                         sales_summary=sales_summary,
                         materials_count=materials_count,
                         recipes_count=recipes_count,
                         products_count=products_count)

# Material routes
@app.route('/materials')
@login_required
def materials():
    """View all materials"""
    materials = Material.query.all()
    materials_with_total = {}

    for material in materials:
        materials_with_total[material.name] = {
            'unit': material.unit,
            'min_quantity': material.min_quantity,
            'batches': [batch.to_dict() for batch in material.batches],
            'total_quantity': material.get_total_quantity()
        }

    return render_template('materials.html', materials=materials_with_total)

@app.route('/materials/add', methods=['GET', 'POST'])
@login_required
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
@login_required
def add_batch(material_name):
    """Add a batch to existing material"""
    material = Material.query.filter_by(name=material_name).first()
    if not material:
        flash('Material not found', 'error')
        return redirect(url_for('materials'))

    if request.method == 'POST':
        quantity = float(request.form.get('quantity'))
        cost_per_unit = float(request.form.get('cost_per_unit'))
        purchase_date = request.form.get('purchase_date')

        success, message = add_material_batch(material_name, quantity, cost_per_unit, purchase_date)
        flash(message, 'success' if success else 'error')
        return redirect(url_for('materials'))

    material_dict = {
        'unit': material.unit,
        'min_quantity': material.min_quantity
    }
    return render_template('add_batch.html', material_name=material_name, material=material_dict)

@app.route('/materials/delete/<material_name>', methods=['POST'])
@login_required
def delete_material_route(material_name):
    """Delete a material"""
    success, message = delete_material(material_name)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('materials'))

# Recipe routes
@app.route('/recipes')
@login_required
def recipes():
    """View all recipes"""
    recipes = Recipe.query.all()
    recipes_with_availability = {}

    for recipe in recipes:
        availability = calculate_recipe_availability(recipe.name)
        recipes_with_availability[recipe.name] = {
            'batch_size': recipe.batch_size,
            'ingredients': [
                {
                    'material': ing.material.name,
                    'quantity': ing.quantity
                }
                for ing in recipe.ingredients
            ],
            'can_make': availability
        }

    return render_template('recipes.html', recipes=recipes_with_availability)

@app.route('/recipes/add', methods=['GET', 'POST'])
@login_required
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
            materials = Material.query.all()
            materials_dict = {m.name: {'unit': m.unit} for m in materials}
            return render_template('add_recipe.html', materials=materials_dict)

        success, message = create_recipe(name, ingredients, batch_size)
        flash(message, 'success' if success else 'error')
        if success:
            return redirect(url_for('recipes'))

    materials = Material.query.all()
    materials_dict = {m.name: {'unit': m.unit} for m in materials}
    return render_template('add_recipe.html', materials=materials_dict)

# Production routes
@app.route('/production')
@login_required
def production():
    """View production page"""
    recipes = Recipe.query.all()
    recipes_dict = {
        r.name: {
            'batch_size': r.batch_size,
            'ingredients': [
                {'material': ing.material.name, 'quantity': ing.quantity}
                for ing in r.ingredients
            ]
        }
        for r in recipes
    }
    return render_template('production.html', recipes=recipes_dict)

@app.route('/production/produce/<recipe_name>', methods=['POST'])
@login_required
def produce(recipe_name):
    """Produce products from a recipe"""
    batches = int(request.form.get('batches', 1))
    success, message = produce_product(recipe_name, batches)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('production'))

# Product routes
@app.route('/products')
@login_required
def products():
    """View all products"""
    products = Product.query.all()
    products_dict = {
        p.name: {
            'quantity': p.quantity,
            'price': p.price
        }
        for p in products
    }
    return render_template('products.html', products=products_dict)

@app.route('/products/set_price/<product_name>', methods=['POST'])
@login_required
def set_price(product_name):
    """Set product price"""
    price = float(request.form.get('price'))
    success, message = set_product_price(product_name, price)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('products'))

# Sales routes
@app.route('/sales')
@login_required
def sales():
    """Point of sale page"""
    products = Product.query.all()
    products_dict = {
        p.name: {
            'quantity': p.quantity,
            'price': p.price
        }
        for p in products
    }
    return render_template('sales.html', products=products_dict)

@app.route('/sales/sell/<product_name>', methods=['POST'])
@login_required
def sell(product_name):
    """Sell a product"""
    quantity = int(request.form.get('quantity', 1))
    success, message = sell_product(product_name, quantity)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('sales'))

@app.route('/sales/history')
@login_required
def sales_history():
    """View sales history"""
    summary = get_sales_summary()
    sales = Sale.query.order_by(Sale.date.desc()).limit(50).all()
    recent_sales = [sale.to_dict() for sale in sales]
    return render_template('sales_history.html', sales=recent_sales, summary=summary)

@app.route('/sales/delete/<int:sale_id>', methods=['POST'])
@login_required
def delete_sale_record(sale_id):
    """Delete a specific sale record"""
    success, message = delete_sale(sale_id)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('sales_history'))

@app.route('/sales/clear', methods=['POST'])
@login_required
def clear_sales():
    """Clear all sales history"""
    success, message = clear_all_sales()
    flash(message, 'success' if success else 'error')
    return redirect(url_for('sales_history'))

# API routes for AJAX
@app.route('/api/alerts')
@login_required
def api_alerts():
    """Get low stock alerts as JSON"""
    alerts = get_low_stock_alerts()
    return jsonify(alerts)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
