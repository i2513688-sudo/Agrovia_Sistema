import unittest
from datetime import date
from unittest.mock import patch

from app import app as flask_app


class DashboardTests(unittest.TestCase):
    def setUp(self):
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1

    @patch("app.tiene_permiso", return_value=True)
    @patch("app.query")
    def test_dashboard_rejects_invalid_date_range(self, query, permission):
        response = self.client.get(
            "/dashboard?fecha_desde=2026-02-30&fecha_hasta=2026-03-01"
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/dashboard")
        query.assert_called_once()
        self.assertIn("SELECT r.nombre AS nombre_rol", query.call_args.args[0])

    @patch("app.tiene_permiso", return_value=True)
    @patch("app.query")
    def test_dashboard_renders_filtered_charts(self, query, permission):
        def return_dashboard_data(sql, params=(), one=False):
            if "SELECT r.nombre AS nombre_rol" in sql:
                return [{"nombre_rol": "GERENTE", "codigo_permiso": "REPORTES_VER"}]
            if "FROM usuarios_roles ur" in sql or "SELECT DISTINCT p.codigo" in sql:
                return []
            if "SELECT COALESCE(SUM(total_operacion), 0) AS total" in sql:
                return {"total": 120.5}
            if "SELECT DATE_FORMAT(fecha_operacion" in sql and "COUNT(*) AS total" in sql:
                return [{"mes": "2026-01", "total": 3}]
            if "SELECT estado, COUNT(*) AS total" in sql:
                return [
                    {"estado": "PENDIENTE_PAGO", "total": 2},
                    {"estado": "COMPLETADA", "total": 1},
                ]
            if "SELECT p.estado, COUNT(*) AS total" in sql:
                return [{"estado": "PENDIENTE", "total": 1, "monto": 75}]
            if "COUNT(*) AS total" in sql:
                return {"total": 2}
            if "o.codigo_operacion" in sql:
                return []
            if "FROM incidencias i" in sql:
                return []
            if "SELECT DATE_FORMAT(fecha_operacion" in sql and "SUM(total_operacion)" in sql:
                return [{"mes": "2026-01", "total": 120.5}]
            if "FROM lotes l" in sql and "comprometido_kg" in sql:
                return [
                    {
                        "id_lote": 10,
                        "codigo_lote": "LOT-10",
                        "producto": "Papa",
                        "produccion_max": 1000,
                        "comprometido_kg": 950,
                    },
                    {
                        "id_lote": 11,
                        "codigo_lote": "LOT-11",
                        "producto": "Choclo",
                        "produccion_max": 2000,
                        "comprometido_kg": 100,
                    },
                    {
                        "id_lote": 12,
                        "codigo_lote": "LOT-12",
                        "producto": "Zanahoria",
                        "produccion_max": 500,
                        "comprometido_kg": 500,
                    },
                ]
            if "SELECT s.id_producto, p.nombre" in sql:
                return [{"id_producto": 4, "nombre": "Papa", "total": 120.5}]
            if "SELECT s.id_producto, DATE_FORMAT" in sql:
                return [{"id_producto": 4, "mes": "2026-01", "total": 120.5}]
            self.fail(f"Unexpected dashboard query: {sql}")

        query.side_effect = return_dashboard_data
        response = self.client.get(
            "/dashboard?fecha_desde=2026-01-10&fecha_hasta=2026-02-20"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Ventas por mes", response.data)
        self.assertIn(b"Operaciones por mes", response.data)
        self.assertIn(b"3 operaci\xc3\xb3n(es)", response.data)
        self.assertIn(b"Operaciones por estado", response.data)
        self.assertIn(b"gr\xc3\xa1fico de barras", response.data)
        self.assertIn(b"gr\xc3\xa1fico circular", response.data)
        self.assertIn(b"aria-label=\"Gr\xc3\xa1fico circular de operaciones por estado\"", response.data)
        self.assertIn(b"stroke-dasharray=", response.data)
        self.assertIn(b"stroke-dashoffset=\"-", response.data)
        self.assertIn(b"COMPLETADA: 1 (33.3%)", response.data)
        self.assertIn(b"Pagos pendientes de revisi", response.data)
        self.assertIn(b"Panel principal", response.data)
        self.assertIn(b"Ventas del periodo", response.data)
        self.assertIn(b"S/ 120.50", response.data)
        self.assertIn(b"Solicitudes pendientes", response.data)
        self.assertIn(b"Entregas en curso", response.data)
        self.assertIn(b"Incidencias pendientes", response.data)
        self.assertIn(b"Papa", response.data)
        self.assertIn(b"LOT-10", response.data)
        self.assertIn(b"Zanahoria", response.data)
        self.assertIn(b"Sin producci\xc3\xb3n estimada disponible", response.data)
        self.assertNotIn(b"LOT-11", response.data)
        self.assertIn(b"2026-01-10", response.data)
        aggregate_calls = [
            call for call in query.call_args_list
            if "fecha_operacion >= %s" in call.args[0]
        ]
        self.assertGreaterEqual(len(aggregate_calls), 5)
        self.assertEqual(
            aggregate_calls[0].args[1],
            (date(2026, 1, 10), date(2026, 2, 20)),
        )


if __name__ == "__main__":
    unittest.main()
