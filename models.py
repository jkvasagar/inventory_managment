"""
Database models for Bakery Inventory Management System
Using SQLAlchemy ORM with PostgreSQL
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Material(db.Model):
    """Raw materials/ingredients"""
    __tablename__ = 'materials'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    unit = db.Column(db.String(50), nullable=False)
    min_quantity = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    batches = db.relationship('MaterialBatch', backref='material', lazy=True,
                            cascade='all, delete-orphan', order_by='MaterialBatch.purchase_date')
    recipe_ingredients = db.relationship('RecipeIngredient', backref='material', lazy=True)

    def __repr__(self):
        return f'<Material {self.name}>'

    def get_total_quantity(self):
        """Calculate total quantity from all batches"""
        return sum(batch.quantity for batch in self.batches)

    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'name': self.name,
            'unit': self.unit,
            'min_quantity': self.min_quantity,
            'total_quantity': self.get_total_quantity(),
            'batches': [batch.to_dict() for batch in self.batches]
        }


class MaterialBatch(db.Model):
    """Material batches for FIFO inventory tracking"""
    __tablename__ = 'material_batches'

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False, index=True)
    quantity = db.Column(db.Float, nullable=False)
    cost_per_unit = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MaterialBatch {self.material.name}: {self.quantity}>'

    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'quantity': self.quantity,
            'cost_per_unit': self.cost_per_unit,
            'purchase_date': self.purchase_date.strftime('%Y-%m-%d')
        }


class Recipe(db.Model):
    """Product recipes"""
    __tablename__ = 'recipes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    batch_size = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    ingredients = db.relationship('RecipeIngredient', backref='recipe', lazy=True,
                                cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Recipe {self.name}>'

    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'name': self.name,
            'batch_size': self.batch_size,
            'ingredients': [ing.to_dict() for ing in self.ingredients]
        }


class RecipeIngredient(db.Model):
    """Ingredients required for each recipe"""
    __tablename__ = 'recipe_ingredients'

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False, index=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False, index=True)
    quantity = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<RecipeIngredient {self.recipe.name}: {self.material.name}>'

    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'material': self.material.name,
            'material_id': self.material_id,
            'quantity': self.quantity,
            'unit': self.material.unit
        }


class Product(db.Model):
    """Finished products ready for sale"""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sales = db.relationship('Sale', backref='product', lazy=True)

    def __repr__(self):
        return f'<Product {self.name}>'

    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'name': self.name,
            'quantity': self.quantity,
            'price': self.price
        }


class Sale(db.Model):
    """Sales transactions"""
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    product_name = db.Column(db.String(100), nullable=False)  # Denormalized for historical record
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<Sale {self.product_name}: ${self.total}>'

    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'product': self.product_name,
            'quantity': self.quantity,
            'price': self.price,
            'total': self.total,
            'date': self.date.strftime('%Y-%m-%d %H:%M:%S')
        }
