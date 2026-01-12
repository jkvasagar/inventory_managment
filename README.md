# 🥐 Bakery Inventory Management System

A comprehensive Command-Line Interface (CLI) tool for managing bakery inventory, recipes, production, and sales.

## Features

### ✨ Core Features
- **FIFO Material Management**: Track raw materials using First-In-First-Out method with batch tracking
- **Recipe Management**: Define recipes for finished products with ingredient requirements
- **Production Tracking**: Automatic material deduction when producing products
- **Low Stock Alerts**: Automatic notifications when materials fall below threshold
- **Point of Sale**: Sell products and track sales revenue
- **Data Persistence**: All data saved to JSON file between sessions

### 🎛️ Three Main Interfaces

#### 1. 🔧 Admin Panel
- Create new materials with units and minimum thresholds
- Create product recipes with ingredients
- Set product prices
- Delete materials and recipes
- View all system data

#### 2. 📦 Inventory Management
- Purchase/add material batches with FIFO tracking
- View all materials with batch details
- Produce products (bake) with automatic material deduction
- View finished products inventory
- Check low stock alerts

#### 3. 💰 Point of Sale (POS)
- Sell products to customers
- View available products and stock levels
- Track sales history and revenue
- View sales summaries by product

## Installation

### Requirements
- Python 3.6 or higher
- No external dependencies required (uses only Python standard library)

### Setup
1. Clone or download the repository
2. Navigate to the directory containing `bakery_inventory.py`
3. Run the script:

```bash
python3 bakery_inventory.py
```

Or make it executable:

```bash
chmod +x bakery_inventory.py
./bakery_inventory.py
```

## Usage Guide

### First Time Setup

1. **Start the application**
   ```bash
   python3 bakery_inventory.py
   ```

2. **Create raw materials** (Admin Panel → Create New Material)
   - Example: Flour, Sugar, Eggs, Butter, etc.
   - Set units: kg, dozen, liters, etc.
   - Set minimum threshold for low stock alerts

3. **Add material batches** (Inventory Management → Add Material Batch)
   - Purchase materials with quantity, cost, and date
   - System automatically tracks using FIFO

4. **Create recipes** (Admin Panel → Create New Recipe)
   - Define product name and batch size
   - Add ingredients with quantities
   - Example: Croissant recipe needs 0.5kg flour, 0.2kg butter, etc.

5. **Set product prices** (Admin Panel → Set Product Price)
   - Set selling price for each product

6. **Start production** (Inventory Management → Produce Product)
   - Select product and number of batches
   - System automatically deducts materials using FIFO
   - Alerts if insufficient materials

7. **Sell products** (POS → Sell Product)
   - Select product and quantity
   - System tracks sales and revenue

### Example Workflow

```
1. Admin creates "Flour" material (unit: kg, min_threshold: 10)
2. Inventory adds batch: 50kg flour @ $2/kg (purchased 2026-01-01)
3. Admin creates "Croissant" recipe (needs 0.5kg flour per batch, batch size: 12)
4. Admin sets croissant price to $3.50
5. Inventory produces 2 batches of croissants (uses 1kg flour via FIFO)
6. POS sells 10 croissants to customer ($35 revenue)
7. System alerts if flour falls below 10kg threshold
```

## Data Structure

### Raw Materials (FIFO Batches)
```json
{
  "materials": {
    "Flour": {
      "unit": "kg",
      "min_threshold": 10,
      "batches": [
        {
          "quantity": 50,
          "cost_per_unit": 2.0,
          "purchase_date": "2026-01-01"
        }
      ]
    }
  }
}
```

### Recipes
```json
{
  "recipes": {
    "Croissant": {
      "batch_size": 12,
      "ingredients": {
        "Flour": 0.5,
        "Butter": 0.2,
        "Sugar": 0.1
      }
    }
  }
}
```

### Products
```json
{
  "products": {
    "Croissant": {
      "quantity": 24,
      "price": 3.50
    }
  }
}
```

### Sales (automatically tracked)
```json
{
  "sales": [
    {
      "product": "Croissant",
      "quantity": 10,
      "price_per_unit": 3.50,
      "total": 35.00,
      "date": "2026-01-12"
    }
  ]
}
```

## FIFO (First-In-First-Out) Method

The system uses FIFO to consume materials:
- Materials are stored in batches with purchase dates
- When producing products, oldest batches are consumed first
- Automatic batch tracking and deduction
- View batch details in Inventory Management

### Example FIFO in Action:
```
Batches of Flour:
1. 2026-01-01: 30kg @ $2/kg
2. 2026-01-05: 40kg @ $2.20/kg
3. 2026-01-10: 20kg @ $2.50/kg

Produce croissants needing 50kg flour:
- Consumes all 30kg from batch 1 (oldest)
- Consumes 20kg from batch 2
- Batch 2 now has 20kg remaining
- Batch 3 untouched
```

## Features in Detail

### ✅ Error Handling
- Invalid user input validation
- Insufficient stock detection
- File corruption recovery
- Missing material/recipe checks
- Graceful keyboard interrupt handling

### 📊 Low Stock Alerts
- Automatic checks after every operation
- Visual warnings when below threshold
- Batch-level quantity tracking
- Proactive inventory management

### 💾 Data Persistence
- All data saved to `bakery_data.json`
- Automatic save after operations
- Manual save/reload options
- Backup-friendly JSON format

### 🎨 User Interface
- Clean, organized menus
- Clear visual feedback (✓, ✗, ⚠️)
- Color-coded sections
- Easy navigation

## Troubleshooting

### Data file corrupted?
- Delete `bakery_data.json` and restart
- System will create a fresh file

### Material not found?
- Create material in Admin Panel first
- Check spelling (case-sensitive)

### Cannot produce product?
- Check if recipe exists (Admin Panel)
- Verify sufficient materials (Inventory Management)
- Check material batch quantities

### Low stock alerts not showing?
- Verify min_threshold is set correctly
- Check total quantity across all batches

## Advanced Tips

1. **Batch Management**: Always check batch details to see which materials are oldest
2. **Cost Tracking**: Track costs per batch to calculate production costs
3. **Sales Analytics**: Use POS sales summary to analyze revenue
4. **Inventory Planning**: Set min_threshold strategically to avoid stockouts
5. **Recipe Optimization**: Test recipes with small batches first

## File Structure

```
inventory_managment/
├── bakery_inventory.py    # Main application script
├── bakery_data.json        # Data file (auto-created)
└── README.md              # This file
```

## Data Backup

The system saves all data to `bakery_data.json`. To backup:
```bash
cp bakery_data.json bakery_data_backup_$(date +%Y%m%d).json
```

## License

This is a demonstration project for educational purposes.

## Support

For issues or questions, please refer to the code comments or modify as needed for your specific requirements.

---

**Happy Baking! 🥐🍰🥖**