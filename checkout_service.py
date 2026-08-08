class CheckoutService:
    def __init__(
        self,
        cart_service,
        product_manager,
        wallet_manager
    ):
        self.cart_service = cart_service
        self.product_manager = product_manager
        self.wallet_manager = wallet_manager

    def checkout(self, user_name):

        cart_items = self.cart_service.get_user_cart_items(
            user_name
        )

        if not cart_items:
            return {
                "status": "error",
                "message": "Cart Is Empty"
            }

        total = 0
        checkout_items = []

        # 1. Validate products and stock
        for item in cart_items:

            product_id = item.get("product_id")
            quantity = item.get("quantity", 0)

            product = self.product_manager.get_product_by_id(
                product_id
            )

            if product is None:
                return {
                    "status": "error",
                    "message": (
                        f"Product {product_id} "
                        "Is No Longer Available"
                    )
                }

            if quantity <= 0:
                return {
                    "status": "error",
                    "message": "Invalid Product Quantity"
                }

            available_quantity = product.get(
                "quantity",
                0
            )

            if quantity > available_quantity:
                return {
                    "status": "error",
                    "message": (
                        f"Not Enough Stock For "
                        f"{product['name']}"
                    )
                }

            price = product.get("price", 0)

            subtotal = price * quantity

            total += subtotal

            checkout_items.append({
                "product": product,
                "product_id": product_id,
                "name": product.get("name"),
                "price": price,
                "quantity": quantity,
                "subtotal": round(subtotal, 2)
            })

        total = round(total, 2)

        # 2. Check wallet
        balance_result = self.wallet_manager.get_balance(
            user_name
        )

        if balance_result.get("status") != "success":
            return balance_result

        current_balance = balance_result.get(
            "balance",
            0
        )

        if current_balance < total:
            return {
                "status": "error",
                "message": "Insufficient Balance",
                "total": total,
                "balance": current_balance
            }

        # Keep old quantities for rollback
        old_quantities = {}

        for item in checkout_items:
            product = item["product"]

            old_quantities[product["id"]] = (
                product["quantity"]
            )

        # 3. Payment
        payment_result = (
            self.wallet_manager.deduct_balance(
                user_name,
                total
            )
        )

        if payment_result.get("status") != "success":
            return payment_result

        try:

            # 4. Reduce stock
            for item in checkout_items:

                product = item["product"]

                product["quantity"] -= item["quantity"]

            self.product_manager._save_products()

            # 5. Clear cart
            clear_result = (
                self.cart_service.clear_user_cart(
                    user_name
                )
            )

            if clear_result != "Cart Cleared Successfully":
                raise RuntimeError(clear_result)

        except Exception:

            # Restore stock
            for item in checkout_items:

                product = item["product"]

                product["quantity"] = (
                    old_quantities[product["id"]]
                )

            self.product_manager._save_products()

            # Refund wallet
            self.wallet_manager.add_balance(
                user_name,
                total
            )

            return {
                "status": "error",
                "message": "Checkout Failed"
            }

        return {
            "status": "success",
            "message": "Checkout Completed Successfully",
            "items": [
                {
                    "product_id": item["product_id"],
                    "name": item["name"],
                    "price": item["price"],
                    "quantity": item["quantity"],
                    "subtotal": item["subtotal"]
                }
                for item in checkout_items
            ],
            "total": total,
            "remaining_balance": payment_result["balance"]
        }