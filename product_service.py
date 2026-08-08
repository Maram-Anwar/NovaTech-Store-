class ProductService:
    def __init__(
        self,
        product_manager,
        image_manager
    ):
        self.product_manager = product_manager
        self.image_manager = image_manager

    def add_product(
        self,
        name,
        category,
        price,
        quantity,
        image_sources=None,
        brand="Nova",
        description="",
        rating=4.5,
        badge="New"
    ):
        product_id = (
            self.product_manager.get_next_product_id()
        )

        image_sources = image_sources or []

        saved_images = []

        for position, source_path in enumerate(
            image_sources,
            start=1
        ):
            is_main = position == 1

            success, result = (
                self.image_manager.save_image(
                    source_path=source_path,
                    product_id=product_id,
                    is_main=is_main,
                    position=position,
                    alt_text=f"{name} image {position}"
                )
            )

            if not success:
                self.image_manager.delete_product_images(
                    product_id
                )

                return result

            saved_images.append(result)

        status = self.product_manager.add_product(
            name=name,
            category=category,
            price=price,
            quantity=quantity,
            images=saved_images,
            product_id=product_id,
            brand=brand,
            description=description,
            rating=rating,
            badge=badge
        )

        if status != "Product Added Successfully":
            self.image_manager.delete_product_images(
                product_id
            )

        return status

    def delete_product(self, product_id):
        status = self.product_manager.delete_product(
            product_id
        )

        if status != "Product Deleted Successfully":
            return status

        success, image_message = (
            self.image_manager.delete_product_images(
                product_id
            )
        )

        if not success:
            return (
                f"{status}, But Image Cleanup Failed: "
                f"{image_message}"
            )

        return status

    def replace_main_image(
        self,
        product_id,
        new_image_source
    ):
        product = self.product_manager.get_product_by_id(
            product_id
        )

        if product is None:
            return "Product Not Found"

        current_images = product.get("images", [])

        success, new_image = (
            self.image_manager.save_image(
                source_path=new_image_source,
                product_id=product_id,
                is_main=True,
                position=1,
                alt_text=f"{product['name']} main image"
            )
        )

        if not success:
            return new_image

        old_main_images = []

        other_images = []

        for image in current_images:
            if image.get("is_main"):
                old_main_images.append(image)
            else:
                other_images.append(image)

        new_images = [new_image]

        for position, image in enumerate(
            other_images,
            start=2
        ):
            image["position"] = position
            image["is_main"] = False

            new_images.append(image)

        status = (
            self.product_manager.update_product_images(
                product_id,
                new_images
            )
        )

        if status != "Product Images Updated Successfully":
            self.image_manager.delete_image(
                new_image["path"]
            )

            return status

        cleanup_errors = []

        for old_image in old_main_images:
            deleted, message = (
                self.image_manager.delete_image(
                    old_image["path"]
                )
            )

            if not deleted:
                cleanup_errors.append(message)

        if cleanup_errors:
            return (
                "Main Image Updated Successfully, "
                "But Old Image Cleanup Failed"
            )

        return "Main Image Updated Successfully"