import unittest
from unittest.mock import patch

from app import app as flask_app


class OrderTrackingMapTests(unittest.TestCase):
    @patch("app.query", side_effect=lambda sql, params=(), one=False: (
        [{"nombre_rol": "COMPRADOR", "codigo_permiso": None}]
        if "SELECT r.nombre AS nombre_rol" in sql else []
    ))
    def test_my_operations_explains_live_gps_tracking_without_fake_reference_map(self, query):
        flask_app.config["TESTING"] = True
        client = flask_app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = 7

        response = client.get("/mis-operaciones")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"La ubicaci\xc3\xb3n mostrada en cada operaci\xc3\xb3n corresponde al "
            b"\xc3\xbaltimo reporte GPS",
            response.data,
        )
        self.assertIn(b"setInterval(refresh, 30000)", response.data)
        self.assertNotIn(
            b'title="Mapa de ubicaci\xc3\xb3n de referencia para el seguimiento del pedido"',
            response.data,
        )


if __name__ == "__main__":
    unittest.main()
