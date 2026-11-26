"""Testes do gerador estático do portfólio."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build as site_build  # noqa: E402


class BuildTests(unittest.TestCase):
    """Cobre geração, idempotência e dados inválidos."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output = Path(self.temp_dir.name) / "index.html"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_generates_expected_html(self) -> None:
        site_build.build(output_path=self.output)
        html_text = self.output.read_text(encoding="utf-8")

        expected = (
            "João Marcelo Neves de Lima",
            'id="projetos"',
            'id="tecnologias"',
            'id="sobre"',
            'id="contato"',
            "PHP",
            "Laravel",
            "C#",
            "Python",
            "Docker",
            "APIs REST",
            "IoT",
            "MySQL",
            ".NET",
            'href="curriculo-joao-marcelo.pdf"',
            "https://github.com/JNeves07",
            'name="viewport" content="width=device-width, initial-scale=1"',
            "Pular para o conteúdo",
        )
        for needle in expected:
            self.assertIn(needle, html_text)

        self.assertNotIn("$", html_text)
        self.assertNotIn("EDITE:", html_text)

    def test_committed_index_is_up_to_date(self) -> None:
        site_build.build(output_path=self.output)

        self.assertEqual(
            self.output.read_text(encoding="utf-8"),
            (ROOT / "index.html").read_text(encoding="utf-8"),
        )

    def test_check_mode_rejects_outdated_index(self) -> None:
        self.output.write_text("<html>antigo</html>\n", encoding="utf-8")

        with self.assertRaises(site_build.BuildError) as context:
            site_build.build(output_path=self.output, check=True)

        self.assertIn("desatualizado", str(context.exception))

    def test_invalid_data_is_rejected(self) -> None:
        data = json.loads((ROOT / "site" / "data.json").read_text(encoding="utf-8"))
        del data["owner"]["name"]
        data["projects"][0]["url"] = "javascript:alert(1)"
        template = (ROOT / "site" / "template.html").read_text(encoding="utf-8")

        with self.assertRaises(site_build.BuildError) as context:
            site_build.render(data, template)

        message = str(context.exception)
        self.assertIn("owner.name", message)
        self.assertIn("projects[0].url", message)

    def test_missing_template_placeholder_is_reported(self) -> None:
        data = json.loads((ROOT / "site" / "data.json").read_text(encoding="utf-8"))

        with self.assertRaises(site_build.BuildError) as context:
            site_build.render(data, "<html>$campo_inexistente</html>")

        self.assertIn("campo_inexistente", str(context.exception))

    def test_invalid_json_returns_friendly_error(self) -> None:
        bad_path = Path(self.temp_dir.name) / "data.json"
        bad_path.write_text('{"site":', encoding="utf-8")

        with self.assertRaises(site_build.BuildError) as context:
            site_build.load_json(bad_path)

        self.assertIn("JSON inválido", str(context.exception))

    def test_cli_build_succeeds(self) -> None:
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            code = site_build.main(["--output", str(self.output)])

        self.assertEqual(code, 0)
        self.assertTrue(self.output.is_file())
        self.assertIn("Site gerado", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
