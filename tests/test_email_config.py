import os
import unittest
from unittest.mock import patch

from mysql.connector import Error as MySQLDatabaseError

from app import app as flask_app, enviar_correo_recuperacion


SMTP_SETTINGS = {
    "SMTP_HOST": "smtp.example.test",
    "SMTP_PORT": "587",
    "SMTP_USER": "mailer@example.test",
    "SMTP_PASSWORD": "test-password",
    "SMTP_FROM": "mailer@example.test",
    "SMTP_USE_TLS": "true",
    "SMTP_USE_SSL": "false",
}


class EmailRecoveryConfigTests(unittest.TestCase):
    @patch.dict(os.environ, SMTP_SETTINGS, clear=True)
    @patch("app.smtplib.SMTP")
    def test_starttls_sends_authenticated_message(self, smtp):
        smtp.return_value.__enter__.return_value.send_message.return_value = {}
        self.assertTrue(
            enviar_correo_recuperacion("user@example.test", "https://example.test/reset")
        )
        server = smtp.return_value.__enter__()
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("mailer@example.test", "test-password")
        server.send_message.assert_called_once()
        mensaje = server.send_message.call_args.args[0]
        self.assertEqual(mensaje["From"], "Agrovia <mailer@example.test>")
        self.assertEqual(mensaje["To"], "user@example.test")
        self.assertIn("Equipo Agrovia", mensaje.get_content())

    @patch.dict(
        os.environ,
        {**SMTP_SETTINGS, "SMTP_PASSWORD": "test pass word"},
        clear=True,
    )
    @patch("app.smtplib.SMTP")
    def test_strips_spaces_from_application_password(self, smtp):
        smtp.return_value.__enter__.return_value.send_message.return_value = {}
        self.assertTrue(
            enviar_correo_recuperacion("user@example.test", "https://example.test/reset")
        )
        smtp.return_value.__enter__().login.assert_called_once_with(
            "mailer@example.test", "testpassword"
        )

    @patch.dict(
        os.environ,
        {**SMTP_SETTINGS, "SMTP_PORT": "465", "SMTP_USE_TLS": "false", "SMTP_USE_SSL": "true"},
        clear=True,
    )
    @patch("app.smtplib.SMTP_SSL")
    def test_implicit_tls_uses_ssl_connection(self, smtp_ssl):
        smtp_ssl.return_value.__enter__.return_value.send_message.return_value = {}
        self.assertTrue(
            enviar_correo_recuperacion("user@example.test", "https://example.test/reset")
        )
        smtp_ssl.assert_called_once()
        smtp_ssl.return_value.__enter__().send_message.assert_called_once()

    @patch.dict(os.environ, SMTP_SETTINGS, clear=True)
    @patch("app.smtplib.SMTP")
    def test_smtp_recipient_rejection_is_reported_as_failure(self, smtp):
        smtp.return_value.__enter__.return_value.send_message.return_value = {
            "user@example.test": (550, b"mailbox unavailable")
        }

        self.assertFalse(
            enviar_correo_recuperacion("user@example.test", "https://example.test/reset")
        )

    @patch.dict(
        os.environ,
        {**SMTP_SETTINGS, "SMTP_PASSWORD": ""},
        clear=True,
    )
    @patch("app.smtplib.SMTP")
    def test_partial_credentials_fail_without_connecting(self, smtp):
        self.assertFalse(
            enviar_correo_recuperacion("user@example.test", "https://example.test/reset")
        )
        smtp.assert_not_called()

    @patch.dict(os.environ, {**SMTP_SETTINGS, "SMTP_PORT": "not-a-port"}, clear=True)
    @patch("app.smtplib.SMTP")
    def test_invalid_port_fails_without_connecting(self, smtp):
        self.assertFalse(
            enviar_correo_recuperacion("user@example.test", "https://example.test/reset")
        )
        smtp.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "APP_BASE_URL": "https://agrovia.example",
            "SMTP_HOST": "smtp.example.test",
            "SMTP_FROM": "mailer@example.test",
        },
        clear=True,
    )
    @patch("app.enviar_correo_recuperacion", return_value=True)
    @patch("app.execute", return_value=123)
    @patch(
        "app.query",
        side_effect=[
            {"id_usuario": 7, "correo": "user@example.test"},
            {"total": 0},
        ],
    )
    def test_recovery_request_sends_link_for_active_user(self, query, execute, send_email):
        flask_app.config["TESTING"] = True
        client = flask_app.test_client()
        client.get("/recuperar-cuenta")
        with client.session_transaction() as session:
            csrf_token = session["_csrf_token"]

        response = client.post(
            "/recuperar-cuenta",
            data={"correo": "user@example.test", "csrf_token": csrf_token},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("La solicitud fue procesada", response.get_data(as_text=True))
        execute.assert_called_once()
        send_email.assert_called_once()
        self.assertEqual(send_email.call_args.args[0], "user@example.test")
        self.assertTrue(
            send_email.call_args.args[1].startswith(
                "https://agrovia.example/restablecer-cuenta/"
            )
        )

    @patch.dict(
        os.environ,
        {
            "APP_BASE_URL": "https://agrovia.example",
            "SMTP_HOST": "smtp.example.test",
            "SMTP_FROM": "mailer@example.test",
        },
        clear=True,
    )
    @patch("app.enviar_correo_recuperacion", return_value=True)
    @patch("app.execute", return_value=123)
    @patch(
        "app.query",
        side_effect=[
            {"id_usuario": 7, "correo": "CuentaRegistrada@example.test"},
            {"total": 0},
        ],
    )
    def test_recovery_sends_to_address_stored_on_account(
        self, query, execute, send_email
    ):
        flask_app.config["TESTING"] = True
        client = flask_app.test_client()
        client.get("/recuperar-cuenta")
        with client.session_transaction() as session:
            csrf_token = session["_csrf_token"]

        response = client.post(
            "/recuperar-cuenta",
            data={"correo": "cuentaregistrada@example.test", "csrf_token": csrf_token},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(send_email.call_args.args[0], "CuentaRegistrada@example.test")

    @patch.dict(
        os.environ,
        {
            "APP_BASE_URL": "https://agrovia.example",
            "SMTP_HOST": "smtp.example.test",
            "SMTP_FROM": "mailer@example.test",
        },
        clear=True,
    )
    @patch("app.enviar_correo_recuperacion", return_value=False)
    @patch("app.execute", side_effect=[123, 1])
    @patch(
        "app.query",
        side_effect=[
            {"id_usuario": 7, "correo": "user@example.test"},
            {"total": 0},
        ],
    )
    def test_failed_email_invalidates_recovery_token(
        self, query, execute, send_email
    ):
        flask_app.config["TESTING"] = True
        client = flask_app.test_client()
        client.get("/recuperar-cuenta")
        with client.session_transaction() as session:
            csrf_token = session["_csrf_token"]

        response = client.post(
            "/recuperar-cuenta",
            data={"correo": "user@example.test", "csrf_token": csrf_token},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(execute.call_count, 2)
        self.assertIn("SET utilizado = 1", execute.call_args.args[0])

    @patch.dict(os.environ, {"SMTP_HOST": "smtp.example.test"}, clear=True)
    @patch("app.query", side_effect=MySQLDatabaseError("database unavailable"))
    def test_recovery_database_error_returns_login_redirect(self, query):
        flask_app.config["TESTING"] = True
        client = flask_app.test_client()
        client.get("/recuperar-cuenta")
        with client.session_transaction() as session:
            csrf_token = session["_csrf_token"]

        response = client.post(
            "/recuperar-cuenta",
            data={"correo": "user@example.test", "csrf_token": csrf_token},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/login")


if __name__ == "__main__":
    unittest.main()
