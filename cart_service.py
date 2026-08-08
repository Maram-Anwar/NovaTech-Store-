
class CartService:
    def __init__(self,cart_manager,product_manager):
        self.cart_manager=cart_manager
        self.product_manager=product_manager

    def get_user_cart_items(self,user_name):
        return self.cart_manager.get_cart_items(user_name)

    def add_product_to_cart(self,user_name,product_id,quantity):
        try:
            product_id = int(product_id)
            quantity = int(quantity)
            if quantity <= 0:
                return "Quantity must be greater than zero!"
        except(ValueError, TypeError):
            return "Product ID & quantity must be a valid integer numbers!"

        product=self.product_manager.get_product_by_id(product_id)
        if product is None:
            return "Product not found!"

        available_quantity = product.get("quantity",0)
        if available_quantity <= 0 :
            return "Product is OUT OF STOCK!"

        current_items=self.cart_manager.get_cart_items(user_name)
        current_quantity=0
        #logic error
        for item in current_items:
            if item.get("product_id")==product_id:
                current_quantity=item.get("quantity",0)
                break

        requested_quantity=current_quantity + quantity
        if requested_quantity > available_quantity:
            return "no enough stock!"

        return self.cart_manager.add_to_cart(user_name,product_id,quantity)

    def update_product_quantity(self,user_name,product_id,quantity):
        try:
            product_id = int(product_id)
            quantity = int(quantity)
            if quantity <= 0:
                return "Quantity must be greater than zero!"
        except (ValueError, TypeError):
            return "Product ID & quantity must be a valid integer numbers!"

        product = self.product_manager.get_product_by_id(product_id)
        if product is None :
            return "Product not found!"

        available_quantity=product.get("quantity",0)
        if quantity > available_quantity :
            return "available quantity isn't enough!"
        return self.cart_manager.update_quantity(user_name,product_id,quantity)

    def remove_product_from_cart(self,user_name,product_id):
        try :
            product_id=int(product_id)
        except (ValueError, TypeError):
            return "product must ba a valid integer number!"
        return self.cart_manager.remove_from_cart(user_name,product_id)

    def clear_user_cart(self,user_name):
        return self.cart_manager.clear_cart(user_name)

    def get_cart_view(self,user_name):
        cart=self.cart_manager.get_cart(user_name)
        cart_items=[]
        total=0
        for item in cart.get("items",[]):
            product_id=item.get("product_id")
            quantity=item.get("quantity",0)

            product = self.product_manager.get_product_by_id(product_id)
            if product is None:
                return {
                    "status": "error",
                    "message": f"Product {product_id} is no longer available"
                }
            price=product.get("price",0)
            subtotal=price*quantity
            total+=subtotal

            images=product.get("images",[])
            main_image=None
            for img in images:
                if img.get("is_main"):
                    main_image=img.get("path")
                    break

            cart_items.append({
                    "product_id" : product.get("id"),
                    "name": product.get("name"),
                    "category" : product.get("category"),
                    "price" : price,
                    "quantity" : quantity,
                    "subtotal" : round(subtotal,2),
                    "main_image" : main_image
            })
        return {
            "username" : user_name,
            "items": cart_items,
            "total" : round(total,2)
        }








