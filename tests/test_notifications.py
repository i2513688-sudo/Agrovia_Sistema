import unittest
from unittest.mock import patch

from app import (
    app as flask_app,
    notificar_administradores,
    notificar_participantes_incidencia,
    notificar_participantes_operacion,
)


class NotificationTests(unittest.TestCase):
    @patch("app.crear_notificacion")
    @patch(
        "app.query",
        return_value=[{"id_usuario": 11}, {"id_usuario": 22}],
    )
    def test_operation_update_notifies_each_participant(self, query, create_notification):
        notificar_participantes_operacion(
            45,
            "Entrega confirmada",
            "La operación fue entregada.",
            "SUCCESS",
        )

        query.assert_called_once()
        self.assertEqual(create_notification.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in create_notification.call_args_list],
            [11, 22],
        )
        self.assertTrue(
            all(call.args[4:] == ("OPERACION", 45)
                for call in create_notification.call_args_list)
        )

    @patch("app.crear_notificacion")
    @patch("app.query", return_value=[{"id_usuario": 5}])
    def test_admin_notification_can_target_permission_holders(
        self, query, create_notification
    ):
        notificar_administradores(
            "Solicitud nueva",
            "Hay una solicitud para revisar.",
            "INFO",
            "SOLICITUD_LOTE",
            9,
            "SOLICITUDES_REVISAR",
        )

        query.assert_called_once()
        self.assertEqual(query.call_args.args[1], ("SOLICITUDES_REVISAR",))
        create_notification.assert_called_once_with(
            5,
            "Solicitud nueva",
            "Hay una solicitud para revisar.",
            "INFO",
            "SOLICITUD_LOTE",
            9,
        )

    @patch("app.crear_notificacion")
    @patch("app.query", return_value=[{"id_usuario": 11}, {"id_usuario": 22}])
    def test_incident_status_notifies_both_operation_participants(
        self, query, create_notification
    ):
        notificar_participantes_incidencia(
            81,
            "Estado de incidencia actualizado",
            "La incidencia fue resuelta.",
            "SUCCESS",
        )

        query.assert_called_once()
        self.assertEqual(create_notification.call_count, 2)
        self.assertTrue(
            all(call.args[4:] == ("INCIDENCIA", 81)
                for call in create_notification.call_args_list)
        )

    @patch("app.es_admin", return_value=True)
    @patch("app.query", return_value={
        "id_incidencia": 81,
        "id_operacion": 45,
        "codigo_incidencia": "INC-81",
        "codigo_operacion": "OP-45",
        "estado": "ABIERTO",
    })
    @patch("app.get_connection")
    def test_incident_state_change_updates_and_notifies_participants(
        self, get_connection, query, es_admin
    ):
        query.side_effect = [
            [{"nombre_rol": "ADMINISTRADOR", "codigo_permiso": None}],
            {
                "id_incidencia": 81,
                "id_operacion": 45,
                "codigo_incidencia": "INC-81",
                "codigo_operacion": "OP-45",
                "estado": "ABIERTO",
            },
        ]
        flask_app.config["TESTING"] = True
        client = flask_app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = 73
            session["_csrf_token"] = "csrf"

        connection = get_connection.return_value
        cursor = connection.cursor.return_value
        cursor.rowcount = 1
        with patch("app.execute") as execute, patch(
            "app.notificar_participantes_incidencia"
        ) as notify:
            response = client.post(
                "/admin/incidencias/81/estado",
                data={
                    "csrf_token": "csrf",
                    "estado": "RESUELTO",
                    "solucion": "Se corrigió el problema.",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(cursor.execute.call_args.args[1][0], "RESUELTO")
        connection.commit.assert_called_once()
        self.assertEqual(execute.call_count, 1)
        notify.assert_called_once()
        self.assertEqual(notify.call_args.args[0], 81)

    @patch("app.execute")
    @patch("app.query", side_effect=[
        [{"nombre_rol": "COMPRADOR", "codigo_permiso": None}],
        [],
    ])
    def test_opening_notifications_marks_only_current_user_as_read(
        self, query, execute
    ):
        flask_app.config["TESTING"] = True
        client = flask_app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = 73

        response = client.get("/notificaciones")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(query.call_args_list[1].args[1], (73,))
        execute.assert_called_once()
        self.assertEqual(execute.call_args.args[1], (73,))


if __name__ == "__main__":
    unittest.main()
