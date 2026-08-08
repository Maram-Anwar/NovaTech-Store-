import json

class CartManager:
    def __init__(self, file_name="carts.json"):
        self.file_name = file_name
        self.carts = self.load_carts()

    def load_carts(self):
        try:
            with open(self.file_name, "r", encoding="utf-8") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save(self):
        with open(self.file_name, "w", encoding="utf-8") as file:
            json.dump(self.carts, file, indent=4)

    def _find_cart(self, user_name):
        user_name = user_name.strip().lower()
        for cart in self.carts:
            if cart.get("username", "").strip().lower() == user_name:
                return cart
        return None

    def get_cart(self, user_name):
        cart = self._find_cart(user_name)
        if cart:
            return cart
        return {"username": user_name.strip().lower(), "items": []}

    def get_cart_items(self, user_name):
        cart = self._find_cart(user_name)
        if cart:
            return cart.get("items", [])
        return []

    def add_to_cart(self, user_name, product_id, quantity):
        user_name = user_name.strip().lower()
        cart = self._find_cart(user_name)

        if not cart:
            cart = {"username": user_name, "items": []}
            self.carts.append(cart)

        for item in cart["items"]:
            if item.get("product_id") == product_id:
                item["quantity"] += quantity
                self._save()
                return "Cart Updated Successfully"

        cart["items"].append({
            "product_id": product_id,
            "quantity": quantity
        })
        
        self._save()
        return "Product Added To Cart"

    def remove_from_cart(self, user_name, product_id):
        cart = self._find_cart(user_name)
        if not cart:
            return "Cart Not Found"

        initial_len = len(cart["items"])
        cart["items"] = [item for item in cart["items"] if item.get("product_id") != product_id]

        if len(cart["items"]) < initial_len:
            self._save()
            return "Product Removed From Cart"
        
        return "Product Not Found In Cart"

    def update_quantity(self, user_name, product_id, quantity):
        cart = self._find_cart(user_name)
        if not cart:
            return "Cart Not Found"

        for item in cart["items"]:
            if item.get("product_id") == product_id:
                item["quantity"] = quantity
                self._save()
                return "Product Quantity Updated Successfully"

        return "Product Not Found In Cart"

    def clear_cart(self, user_name):
        cart = self._find_cart(user_name)
        if cart:
            cart["items"] = []
            self._save()
            return "Cart Cleared Successfully"
        return "Cart Not Found"