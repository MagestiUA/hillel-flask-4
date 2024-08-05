import unittest
import random
from peewee import SqliteDatabase
from app import app
from peewee_db import Product, Category


test_db = SqliteDatabase(":memory:")


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        test_db.bind([Product])
        test_db.connect()
        test_db.create_tables([Product, Category])
        self.category = Category.create(name="TestCategory")
        self.existing_product = Product.create(name="New_Test_Product", price=200, category=self.category)
        Product.get_or_create(name="Duplicate", price=100, category=self.category)

    def tearDown(self):
        Product.delete().where(Product.name == "Duplicate").execute()
        Product.delete().where(Product.name.startswith("test_")).execute()
        test_db.drop_tables([Product])
        test_db.close()

    def test_products_get(self):
        response = self.app.get("/products")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 2)

    def test_products_post(self):
        unique_product_name = f"test_{random.randint(1, 1000000)}"
        response = self.app.post("/products", json={"name": unique_product_name, "price": "100", "category_id": self.category.id})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["name"], unique_product_name)
        self.assertEqual(float(response.json["price"]), 100)
        product = Product.get(Product.name == unique_product_name)
        self.app.delete(f"/products/{product.id}")

    def test_product_post_duplicate_name(self):
        response = self.app.post("/products", json={"name": "Duplicate", "price": 100, "category_id": self.category.id})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "Product with this name already exists")

    def test_product_post_invalid_data(self):
        response = self.app.post("/products", json={"name": "Invalid", "price": "invalid"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "Price must be a number")

    def test_product_delete_existing(self):
        product = Product.get(Product.name == "New_Test_Product")
        response = self.app.delete(f"/products/{product.id}")
        self.assertEqual(response.status_code, 204)

    def test_product_delete_non_existing(self):
        product_id_not_in_db = 3
        response = self.app.delete(f"/products/{product_id_not_in_db}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"], "Product not found")
