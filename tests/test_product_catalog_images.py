import unittest
from unittest.mock import patch

from app import app as flask_app


class ProductCatalogImageTests(unittest.TestCase):
    @patch(
        "app.query",
        side_effect=[
            [
                {"id_producto": 1, "nombre": "Ajo", "categoria": "Hortalizas", "descripcion": "Producto agrícola del piloto"},
                {"id_producto": 2, "nombre": "Olluco", "categoria": "Tubérculos", "descripcion": "Producto agrícola del piloto"},
            ],
            [],
        ],
    )
    def test_homepage_hides_products_without_images(self, query):
        flask_app.config["TESTING"] = True
        response = flask_app.test_client().get("/")
        page = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("img/ajo.png", page)
        self.assertNotIn(">Olluco<", page)
        self.assertNotIn("Producto agrícola del piloto", page)

    @patch(
        "app.query",
        side_effect=[
            [
                {"nombre": "Ajo", "categoria": "Hortalizas", "descripcion": "Producto agrícola del piloto"},
                {"nombre": "Apio", "categoria": "Hortalizas", "descripcion": "Producto agrícola del piloto"},
                {"nombre": "Col/Repollo", "categoria": "Hortalizas", "descripcion": "Producto agrícola del piloto"},
                {"nombre": "Lechuga", "categoria": "Hortalizas", "descripcion": "Producto agrícola del piloto"},
                {"nombre": "Quinua", "categoria": "Granos", "descripcion": "Producto agrícola del piloto"},
                {"nombre": "Olluco", "categoria": "Tubérculos", "descripcion": "Producto agrícola del piloto"},
            ],
            [{"nombre": "Hortalizas"}, {"nombre": "Granos"}],
        ],
    )
    def test_catalog_shows_requested_images_and_hides_products_without_images(self, query):
        flask_app.config["TESTING"] = True
        response = flask_app.test_client().get("/productos")
        page = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        for image in ("ajo.png", "apio.png", "col.png", "lechuga.png", "quinua.png"):
            self.assertIn(f"img/{image}", page)
        self.assertNotIn(">Olluco<", page)
        self.assertNotIn("Producto agrícola del piloto", page)
        self.assertEqual(page.count('class="producto-card"'), 5)


if __name__ == "__main__":
    unittest.main()
