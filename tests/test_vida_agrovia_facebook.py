import unittest
from unittest.mock import patch

from app import app as flask_app


class VidaAgroviaFacebookTests(unittest.TestCase):
    @patch("app.query", return_value=[])
    def test_featured_applied_talk_links_to_agrovia_facebook_post(self, query):
        flask_app.config["TESTING"] = True
        response = flask_app.test_client().get("/vida-agrovia")

        self.assertEqual(response.status_code, 200)
        image_position = response.data.index(b'class="capacitacion-img"')
        facebook_position = response.data.index(
            b'href="https://www.facebook.com/share/p/1FVxmshvxB/"'
        )
        content_position = response.data.index(b'class="capacitacion-body"')
        self.assertLess(image_position, facebook_position)
        self.assertLess(facebook_position, content_position)
        self.assertIn(b"Ver charla aplicada en Facebook", response.data)
        link_markup = response.data[facebook_position:content_position]
        self.assertIn(b'target="_blank"', link_markup)
        self.assertIn(b'rel="noopener noreferrer"', link_markup)
        self.assertNotIn(b"class=\"btn-contenido\"", response.data)
        self.assertNotIn(b"Ver contenido", response.data)


if __name__ == "__main__":
    unittest.main()
