"""
Inventory Management Tools

Showcases CaveAgent advantage: Loop through warehouses/products,
check stock levels, and create reorders based on thresholds - all in one turn.

JSON function calling would need:
1. get_warehouses
2. For each warehouse: get_stock_levels  (N calls)
3. For each low stock: create_reorder    (M calls)

CaveAgent: Single turn with loop + conditional
"""

from typing import Dict, Any, List, Optional


# Simulated inventory data
_WAREHOUSES = {
    "warehouse_east": {
        "location": "New York",
        "products": {
            "SKU001": {"name": "Laptop", "quantity": 15, "min_threshold": 20, "reorder_quantity": 50},
            "SKU002": {"name": "Mouse", "quantity": 150, "min_threshold": 100, "reorder_quantity": 200},
            "SKU003": {"name": "Keyboard", "quantity": 8, "min_threshold": 30, "reorder_quantity": 100},
        }
    },
    "warehouse_west": {
        "location": "Los Angeles",
        "products": {
            "SKU001": {"name": "Laptop", "quantity": 45, "min_threshold": 20, "reorder_quantity": 50},
            "SKU002": {"name": "Mouse", "quantity": 25, "min_threshold": 100, "reorder_quantity": 200},
            "SKU004": {"name": "Monitor", "quantity": 5, "min_threshold": 15, "reorder_quantity": 40},
        }
    },
    "warehouse_central": {
        "location": "Chicago",
        "products": {
            "SKU001": {"name": "Laptop", "quantity": 60, "min_threshold": 20, "reorder_quantity": 50},
            "SKU003": {"name": "Keyboard", "quantity": 200, "min_threshold": 30, "reorder_quantity": 100},
            "SKU005": {"name": "Headphones", "quantity": 12, "min_threshold": 25, "reorder_quantity": 75},
        }
    }
}

_reorder_log = []


def get_warehouses() -> List[str]:
    """
    Get list of all warehouse IDs.

    Returns:
        List[str]: List of warehouse identifiers
        Example: ["warehouse_east", "warehouse_west", "warehouse_central"]
    """
    return list(_WAREHOUSES.keys())


def get_stock_levels(warehouse_id: str) -> Dict[str, Any]:
    """
    Get current stock levels for all products in a warehouse.

    Parameters:
        warehouse_id (str): [Required] Warehouse identifier (e.g., "warehouse_east")

    Returns:
        dict: {
            "warehouse_id": str,
            "location": str,
            "products": {
                "SKU": {
                    "name": str,
                    "quantity": int,
                    "min_threshold": int,
                    "needs_reorder": bool
                }
            }
        }
    """
    if warehouse_id not in _WAREHOUSES:
        return {"error": f"Warehouse '{warehouse_id}' not found"}

    warehouse = _WAREHOUSES[warehouse_id]
    products_status = {}

    for sku, data in warehouse["products"].items():
        products_status[sku] = {
            "name": data["name"],
            "quantity": data["quantity"],
            "min_threshold": data["min_threshold"],
            "needs_reorder": data["quantity"] < data["min_threshold"]
        }

    return {
        "warehouse_id": warehouse_id,
        "location": warehouse["location"],
        "products": products_status
    }


def create_reorder(warehouse_id: str, sku: str, quantity: Optional[int] = None) -> Dict[str, Any]:
    """
    Create a reorder request for a product.

    Parameters:
        warehouse_id (str): [Required] Warehouse identifier
        sku (str): [Required] Product SKU to reorder
        quantity (int): [Optional] Quantity to order. Uses default reorder_quantity if not specified.

    Returns:
        dict: {
            "order_id": str,
            "warehouse_id": str,
            "sku": str,
            "product_name": str,
            "quantity": int,
            "status": str
        }
    """
    if warehouse_id not in _WAREHOUSES:
        return {"error": f"Warehouse '{warehouse_id}' not found"}

    warehouse = _WAREHOUSES[warehouse_id]
    if sku not in warehouse["products"]:
        return {"error": f"SKU '{sku}' not found in {warehouse_id}"}

    product = warehouse["products"][sku]
    order_qty = quantity if quantity else product["reorder_quantity"]

    order = {
        "order_id": f"RO-{warehouse_id[-4:]}-{sku}-{len(_reorder_log)+1:03d}",
        "warehouse_id": warehouse_id,
        "sku": sku,
        "product_name": product["name"],
        "quantity": order_qty,
        "status": "created"
    }

    _reorder_log.append(order)
    return order


def get_low_stock_summary() -> Dict[str, Any]:
    """
    Get a summary of all products below minimum threshold across all warehouses.

    Returns:
        dict: {
            "total_low_stock_items": int,
            "warehouses_affected": int,
            "items": [{"warehouse": str, "sku": str, "name": str, "quantity": int, "threshold": int}]
        }
    """
    low_stock_items = []

    for wh_id, warehouse in _WAREHOUSES.items():
        for sku, data in warehouse["products"].items():
            if data["quantity"] < data["min_threshold"]:
                low_stock_items.append({
                    "warehouse": wh_id,
                    "sku": sku,
                    "name": data["name"],
                    "quantity": data["quantity"],
                    "threshold": data["min_threshold"]
                })

    warehouses_affected = len(set(item["warehouse"] for item in low_stock_items))

    return {
        "total_low_stock_items": len(low_stock_items),
        "warehouses_affected": warehouses_affected,
        "items": low_stock_items
    }


def get_reorder_log() -> List[Dict[str, Any]]:
    """Get all reorders created (for testing)."""
    return _reorder_log.copy()


def clear_reorder_log():
    """Clear reorder log (for testing)."""
    global _reorder_log
    _reorder_log = []


tools = [
    get_warehouses,
    get_stock_levels,
    create_reorder,
    get_low_stock_summary
]
