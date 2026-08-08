import os
import shutil
from pathlib import Path
from uuid import uuid4


class ImageManager:
    def __init__(self, images_directory="images/products"):
        self.images_directory = images_directory

        os.makedirs(
            self.images_directory,
            exist_ok=True
        )

    def save_image(
        self,
        source_path,
        product_id,
        is_main=False,
        position=1,
        alt_text = ""
    ):
        if not os.path.exists(source_path):
            return False, "Image File Not Found"

        product_folder = os.path.join(
            self.images_directory,
            str(product_id)
        )

        os.makedirs(
            product_folder,
            exist_ok=True
        )

        extension = Path(source_path).suffix.lower()

        unique_id = uuid4().hex[:8]

        if is_main:
            file_name = f"main_{unique_id}{extension}"
        else:
            file_name = f"image_{position}_{unique_id}{extension}"

        destination_path = os.path.join(
            product_folder,
            file_name
        )

        try:
            shutil.copy2(
                source_path,
                destination_path
            )

        except Exception:
            return False, "Failed To Save Image"

        image_data = {
            "path": destination_path.replace("\\", "/"),
            "is_main": is_main,
            "position": position,
            "alt_text": alt_text
        }

        return True, image_data

    def delete_image(self, image_path):
        if not os.path.exists(image_path):
            return False, "Image Not Found"

        try:
            os.remove(image_path)

        except Exception:
            return False, "Failed To Delete Image"

        return True, "Image Deleted Successfully"

    def delete_product_images(self, product_id):
        product_folder = os.path.join(
            self.images_directory,
            str(product_id)
        )

        if not os.path.exists(product_folder):
            return True, "No Images Found"

        try:
            shutil.rmtree(product_folder)

        except Exception:
            return False, "Failed To Delete Product Images"

        return True, "Product Images Deleted Successfully"

    def image_exists(self, image_path):
        return os.path.exists(image_path)

    def get_product_images(self, product_id):
        product_folder = os.path.join(
            self.images_directory,
            str(product_id)
        )

        if not os.path.exists(product_folder):
            return []

        images = []

        for file_name in sorted(os.listdir(product_folder)):
            images.append(
                os.path.join(
                    product_folder,
                    file_name
                ).replace("\\", "/")
            )

        return images