import json


class ProductManager:
    def __init__(self, file_name="products.json"):
        self.file_name = file_name
        self.database = self.load_products()

    def load_products(self):
        try:
            with open(self.file_name, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def get_all_products(self):
        return self.database.copy()

    def get_product_by_id(self, product_id):
        for product in self.database:
            if product.get("id") == product_id:
                return product
        return None

    def get_next_product_id(self):
        if not self.database:
            return 1
        return max(int(product.get("id", 0)) for product in self.database) + 1

    def add_product(self, name, category, price, quantity, images=None, product_id=None,
                    brand="Nova", description="", rating=4.5, badge="New"):
        name = str(name or "").strip()
        category = str(category or "").strip()
        brand = str(brand or "Nova").strip() or "Nova"
        description = str(description or "").strip()
        badge = str(badge or "New").strip()

        if not name:
            return "Product Name Is Required"
        if not category:
            return "Product Category Is Required"
        if price <= 0:
            return "Product Price Must Be Greater Than Zero"
        if quantity < 0:
            return "Product Quantity Cannot Be Negative"
        try:
            rating = max(0.0, min(5.0, float(rating)))
        except (TypeError, ValueError):
            rating = 4.5

        new_product = {
            "id": product_id if product_id else self.get_next_product_id(),
            "name": name,
            "category": category,
            "price": float(price),
            "quantity": int(quantity),
            "brand": brand,
            "description": description,
            "rating": rating,
            "badge": badge,
            "images": images or [],
        }
        self.database.append(new_product)
        self._save_products()
        return "Product Added Successfully"

    def update_product(self, product_id, name=None, category=None, price=None, quantity=None,
                       brand=None, description=None, rating=None, badge=None):
        product = self.get_product_by_id(product_id)
        if product is None:
            return "Product Not Found"

        if name is not None:
            clean = str(name).strip()
            if not clean:
                return "Product Name Cannot Be Empty"
            product["name"] = clean
        if category is not None:
            clean = str(category).strip()
            if not clean:
                return "Product Category Cannot Be Empty"
            product["category"] = clean
        if price is not None:
            if price <= 0:
                return "Product Price Must Be Greater Than Zero"
            product["price"] = float(price)
        if quantity is not None:
            if quantity < 0:
                return "Product Quantity Cannot Be Negative"
            product["quantity"] = int(quantity)
        if brand is not None:
            product["brand"] = str(brand).strip() or "Nova"
        if description is not None:
            product["description"] = str(description).strip()
        if badge is not None:
            product["badge"] = str(badge).strip()
        if rating is not None:
            try:
                product["rating"] = max(0.0, min(5.0, float(rating)))
            except (TypeError, ValueError):
                return "Invalid Product Rating"

        self._save_products()
        return "Product Updated Successfully"

    def update_product_images(self, product_id, images):
        product = self.get_product_by_id(product_id)
        if product is None:
            return "Product Not Found"
        product["images"] = images
        self._save_products()
        return "Product Images Updated Successfully"

    def delete_product(self, product_id):
        product = self.get_product_by_id(product_id)
        if product is None:
            return "Product Not Found"
        self.database.remove(product)
        self._save_products()
        return "Product Deleted Successfully"

    def search_products(self, keyword):
        keyword = str(keyword or "").strip().lower()
        fields = ("name", "category", "brand", "description", "badge")
        return [
            product for product in self.database
            if any(keyword in str(product.get(field, "")).lower() for field in fields)
        ]

    def get_products_by_category(self, category):
        category = str(category or "").strip().lower()
        return [p for p in self.database if str(p.get("category", "")).lower() == category]

    def get_categories(self):
        return sorted({str(p.get("category", "")).strip() for p in self.database if str(p.get("category", "")).strip()})

    def get_low_stock_products(self, stock_limit=5):
        return [p for p in self.database if int(p.get("quantity", 0)) <= stock_limit]

    def get_statistics(self):
        total_items = sum(int(p.get("quantity", 0)) for p in self.database)
        inventory_value = sum(int(p.get("quantity", 0)) * float(p.get("price", 0)) for p in self.database)
        ratings = [float(p.get("rating", 0)) for p in self.database if p.get("rating") is not None]
        return {
            "total_products": len(self.database),
            "total_items": total_items,
            "inventory_value": inventory_value,
            "out_of_stock": sum(1 for p in self.database if int(p.get("quantity", 0)) == 0),
            "low_stock": sum(1 for p in self.database if int(p.get("quantity", 0)) <= 5),
            "categories": len(self.get_categories()),
            "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else 0,
        }

    def _save_products(self):
        with open(self.file_name, "w", encoding="utf-8") as file:
            json.dump(self.database, file, indent=4, ensure_ascii=False)
