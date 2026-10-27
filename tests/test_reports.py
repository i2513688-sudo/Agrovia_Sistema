import io
import unittest
from datetime import date, datetime
from unittest.mock import patch

from openpyxl import load_workbook

from app import app as flask_app


class DownloadableReportTests(unittest.TestCase):
    def setUp(self):
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 7

    @staticmethod
    def authenticated_query(fallback):
        def respond(sql, params=(), one=False):
            if "SELECT r.nombre AS nombre_rol" in sql:
                return [{"nombre_rol": "GERENTE", "codigo_permiso": "REPORTES_VER"}]
            return fallback
        return respond

    @patch("app.tiene_permiso", return_value=True)
    @patch("app.query")
    def test_excel_report_contains_filtered_rows_and_safe_text(self, query, permission):
        rows = [{
            "Código": "=1+1",
            "Fecha": datetime(2026, 1, 12, 10, 30),
            "Producto": "Papa",
            "Productor": "Ana",
            "Comprador": "Luis",
            "Total (S/)": 125.5,
            "Estado": "PENDIENTE_PAGO",
        }]
        query.side_effect = self.authenticated_query(rows)

        response = self.client.get(
            "/admin/reportes/operaciones/excel"
            "?fecha_desde=2026-01-01&fecha_hasta=2026-01-31"
            "&estado=PENDIENTE_PAGO"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            response.content_type,
        )
        self.assertIn("reporte_operaciones_", response.headers["Content-Disposition"])
        libro = load_workbook(io.BytesIO(response.data), data_only=False)
        hoja = libro["Reporte"]
        self.assertEqual(hoja["A2"].value, "Código")
        self.assertEqual(hoja["A3"].value, "'=1+1")
        self.assertEqual(hoja["C3"].value, "Papa")
        self.assertEqual(hoja.freeze_panes, "A3")
        self.assertEqual(
            query.call_args.args[1],
            (date(2026, 1, 1), date(2026, 1, 31), "PENDIENTE_PAGO"),
        )

    @patch("app.tiene_permiso", return_value=True)
    @patch("app.query")
    def test_pdf_report_generates_valid_file_with_headers(self, query, permission):
        query.side_effect = self.authenticated_query([])
        response = self.client.get("/admin/reportes/entregas/pdf")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertTrue(response.data.startswith(b"%PDF-"))
        self.assertIn("reporte_entregas_", response.headers["Content-Disposition"])

    @patch("app.tiene_permiso", return_value=True)
    @patch("app.query")
    def test_download_rejects_state_not_valid_for_report(self, query, permission):
        response = self.client.get(
            "/admin/reportes/operaciones/pdf?estado=EN_RUTA"
        )

        self.assertEqual(response.status_code, 400)
        query.assert_called_once()

    @patch("app.tiene_permiso", return_value=True)
    @patch("app.query")
    def test_download_rejects_reversed_date_range(self, query, permission):
        response = self.client.get(
            "/admin/reportes/pagos/excel"
            "?fecha_desde=2026-02-01&fecha_hasta=2026-01-01"
        )

        self.assertEqual(response.status_code, 400)
        query.assert_called_once()

    @patch("app.tiene_permiso", return_value=True)
    @patch("app.query")
    def test_report_page_lists_exports_and_resets_incompatible_state(
        self, query, permission
    ):
        query.side_effect = self.authenticated_query([])
        response = self.client.get(
            "/admin/reportes?tipo=pagos&estado=EN_TRANSPORTE"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Descargar Excel", response.data)
        self.assertIn(b"Descargar PDF", response.data)
        self.assertIn(b"Pagos", response.data)
        self.assertIn(b"Todos los estados", response.data)


if __name__ == "__main__":
    unittest.main()
