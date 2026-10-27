import json
import os
import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from app import app as flask_app, calcular_ruta_osrm


class LogisticsTrackingTests(unittest.TestCase):
    def setUp(self):
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()

    @patch.dict(os.environ, {"OSRM_ROUTING_URL": "https://routing.example"})
    @patch("app.urlopen")
    def test_route_calculation_uses_road_distance_and_estimated_duration(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps({
            "code": "Ok",
            "routes": [{"distance": 12345, "duration": 3601}],
        }).encode("utf-8")

        route = calcular_ruta_osrm(-12.1, -75.2, -12.3, -75.4)

        self.assertEqual(route["distancia_km"], Decimal("12.35"))
        self.assertEqual(route["duracion_estimada_min"], 61)
        urlopen.assert_called_once()

    @patch("app.urlopen")
    def test_route_calculation_does_not_call_service_with_invalid_coordinates(self, urlopen):
        self.assertIsNone(calcular_ruta_osrm(91, 0, 0, 0))
        urlopen.assert_not_called()

    @patch("app.query", side_effect=[
        [{"nombre_rol": "TRANSPORTISTA", "codigo_permiso": "TRANSPORTE_ACTUALIZAR"}],
        [],
    ])
    def test_transport_page_renders_for_authenticated_transport_user(self, query):
        with self.client.session_transaction() as session:
            session["user_id"] = 7

        response = self.client.get("/mis-transportes")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Mis transportes", response.data)

    @patch("app.query")
    @patch("app.obtener_transporte_seguimiento", return_value={
        "id_transporte": 12,
        "id_operacion": 34,
        "estado": "EN_RUTA",
        "id_usuario_transportista": 7,
    })
    def test_transport_owner_can_read_latest_gps_location(self, transporte, query):
        query.side_effect = [
            [{"nombre_rol": "TRANSPORTISTA", "codigo_permiso": "TRANSPORTE_ACTUALIZAR"}],
            {
                "latitud": Decimal("-12.1"),
                "longitud": Decimal("-75.2"),
                "precision_m": Decimal("8.5"),
                "fecha_reporte": datetime(2026, 10, 27, 12, 0),
            },
        ]
        with self.client.session_transaction() as session:
            session["user_id"] = 7

        response = self.client.get("/api/transportes/12/ubicacion")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ubicacion"]["latitud"], -12.1)

    @patch("app.usuario_participa_en_operacion", return_value=False)
    @patch("app.es_admin", return_value=False)
    @patch("app.obtener_transporte_seguimiento", return_value={
        "id_transporte": 12,
        "id_operacion": 34,
        "estado": "EN_RUTA",
        "id_usuario_transportista": 99,
    })
    @patch("app.query", return_value=[
        {"nombre_rol": "COMPRADOR", "codigo_permiso": None}
    ])
    def test_unrelated_user_cannot_read_transport_location(
        self, query, transporte, es_admin, participante
    ):
        with self.client.session_transaction() as session:
            session["user_id"] = 7

        response = self.client.get("/api/transportes/12/ubicacion")

        self.assertEqual(response.status_code, 403)

    @patch("app.query")
    def test_buyer_sees_destination_and_live_tracking_map(self, query):
        query.side_effect = [
            [{"nombre_rol": "COMPRADOR", "codigo_permiso": None}],
            [{
                "id_operacion": 34,
                "codigo_operacion": "OP-034",
                "total_operacion": Decimal("100.00"),
                "estado": "EN_PROCESO",
                "producto": "Papa",
                "codigo_lote": "LT-034",
                "id_transporte": 12,
                "codigo_transporte": "TR-012",
                "estado_transporte": "LLEGADA_DESTINO",
                "direccion_entrega": "Av. Central 123",
                "latitud_destino": Decimal("-12.05"),
                "longitud_destino": Decimal("-77.03"),
                "transportista": "Transporte Agro",
                "placa": "ABC-123",
                "distancia_km": Decimal("25.5"),
                "duracion_estimada_min": 60,
                "latitud_actual": Decimal("-12.06"),
                "longitud_actual": Decimal("-77.02"),
                "fecha_ubicacion": datetime(2026, 10, 27, 12, 0),
                "id_pago": None,
                "puede_pagar": 0,
                "puede_calificar": 0,
            }],
            [],
            [],
        ]
        with self.client.session_transaction() as session:
            session["user_id"] = 7

        response = self.client.get("/mis-operaciones")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Llegada verificada por administraci", response.data)
        self.assertIn(b"Ver destino en Google Maps", response.data)
        self.assertIn(b"Ver ruta desde la ubicaci", response.data)
        self.assertIn(b"Av. Central 123", response.data)
        self.assertIn(b"/api/transportes/12/ubicacion", response.data)


if __name__ == "__main__":
    unittest.main()
