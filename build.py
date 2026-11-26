"""Gera o index.html do portfólio a partir de site/data.json."""

from __future__ import annotations

import argparse
import html
import json
import re
import string
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = ROOT / "site" / "data.json"
DEFAULT_TEMPLATE_PATH = ROOT / "site" / "template.html"
DEFAULT_OUTPUT_PATH = ROOT / "index.html"

URL_PREFIXES = ("https://", "http://", "mailto:")
RELATIVE_FILE = re.compile(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*")


class BuildError(Exception):
    """Erro amigável de dados ou template do site."""


def escape(value: Any) -> str:
    """Escapa valores dinâmicos antes de inseri-los no HTML."""
    return html.escape(str(value), quote=True)


def load_json(path: Path) -> dict[str, Any]:
    """Lê um JSON com mensagens claras de erro."""
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise BuildError(f"Arquivo não encontrado: {path}") from exc
    except OSError as exc:
        raise BuildError(f"Não foi possível ler {path}: {exc}") from exc

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise BuildError(
            f"JSON inválido em {path} (linha {exc.lineno}, coluna {exc.colno})."
        ) from exc

    if not isinstance(data, dict):
        raise BuildError(f"Dados inválidos em {path}: a raiz deve ser um objeto JSON.")
    return data


def _is_text(value: Any) -> bool:
    """Verifica se o valor é um texto não vazio."""
    return isinstance(value, str) and bool(value.strip())


def _is_url(value: Any, *, allow_anchor: bool = False) -> bool:
    """Verifica se o link usa um esquema seguro."""
    if not _is_text(value) or any(char.isspace() for char in value):
        return False
    if allow_anchor and value.startswith("#"):
        return True
    return value.startswith(URL_PREFIXES)


def _is_resume(value: Any) -> bool:
    """Aceita um PDF relativo ou uma URL http(s)."""
    if isinstance(value, str) and value.startswith(URL_PREFIXES[:2]):
        return True
    return (
        isinstance(value, str)
        and not value.startswith(("/", "#"))
        and value.endswith(".pdf")
        and bool(RELATIVE_FILE.fullmatch(value))
    )


def _text(parent: dict[str, Any], key: str, errors: list[str], path: str) -> None:
    """Valida um texto obrigatório dentro de um objeto."""
    value = parent.get(key)
    if not _is_text(value):
        errors.append(f"{path}.{key} deve ser um texto não vazio")


def _mapping(parent: dict[str, Any], key: str, errors: list[str], path: str) -> dict[str, Any] | None:
    """Valida um objeto obrigatório dentro de outro objeto."""
    value = parent.get(key)
    if not isinstance(value, dict):
        errors.append(f"{path}.{key} deve ser um objeto")
        return None
    return value


def _items(parent: dict[str, Any], key: str, errors: list[str], path: str) -> list[Any]:
    """Valida uma lista não vazia dentro de um objeto."""
    value = parent.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"{path}.{key} deve ser uma lista não vazia")
        return []
    return value


def _text_list(parent: dict[str, Any], key: str, errors: list[str], path: str) -> None:
    """Valida uma lista de textos."""
    value = parent.get(key)
    if not isinstance(value, list) or not all(_is_text(item) for item in value):
        errors.append(f"{path}.{key} deve ser uma lista de textos não vazios")


def validate_data(data: dict[str, Any]) -> list[str]:
    """Retorna os problemas encontrados nos dados do portfólio."""
    errors: list[str] = []

    site = _mapping(data, "site", errors, "dados")
    if site:
        _text(site, "title", errors, "site")
        _text(site, "description", errors, "site")

    owner = _mapping(data, "owner", errors, "dados")
    if owner:
        for key in ("name", "short_name", "role", "lead"):
            _text(owner, key, errors, "owner")
        if not _is_resume(owner.get("resume")):
            errors.append("owner.resume deve ser um PDF relativo ou URL http(s)")

        links = _mapping(owner, "links", errors, "owner")
        if links:
            for key in ("github", "linkedin", "email", "whatsapp"):
                if not _is_url(links.get(key)):
                    errors.append(f"owner.links.{key} deve ser uma URL http(s) ou mailto:")

        card = _mapping(owner, "api_card", errors, "owner")
        if card:
            for key in ("status", "cargo", "onde", "status_value"):
                _text(card, key, errors, "owner.api_card")
            _text_list(card, "stack", errors, "owner.api_card")
            _text_list(card, "formacao", errors, "owner.api_card")

    nav = _items(data, "nav", errors, "dados")
    for index, item in enumerate(nav):
        path = f"nav[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path} deve ser um objeto")
            continue
        _text(item, "label", errors, path)
        if not _is_url(item.get("href"), allow_anchor=True):
            errors.append(f"{path}.href deve ser uma âncora ou URL http(s)")

    projects = _items(data, "projects", errors, "dados")
    for index, item in enumerate(projects):
        path = f"projects[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path} deve ser um objeto")
            continue
        for key in ("name", "description", "link_label"):
            _text(item, key, errors, path)
        if not _is_url(item.get("url")):
            errors.append(f"{path}.url deve ser uma URL http(s)")

    if not _is_url(data.get("repositories_url")):
        errors.append("repositories_url deve ser uma URL http(s)")

    technologies = _items(data, "technologies", errors, "dados")
    for index, item in enumerate(technologies):
        path = f"technologies[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path} deve ser um objeto")
            continue
        _text(item, "category", errors, path)
        _text(item, "items", errors, path)

    about = _mapping(data, "about", errors, "dados")
    if about:
        _text_list(about, "paragraphs", errors, "about")

    experience = data.get("experience")
    if not isinstance(experience, list):
        errors.append("experience deve ser uma lista")
    else:
        for index, item in enumerate(experience):
            path = f"experience[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{path} deve ser um objeto")
                continue
            _text(item, "title", errors, path)
            _text(item, "meta", errors, path)
            _text_list(item, "highlights", errors, path)

    education = data.get("education")
    if not isinstance(education, list):
        errors.append("education deve ser uma lista")
    else:
        for index, item in enumerate(education):
            path = f"education[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{path} deve ser um objeto")
                continue
            _text(item, "title", errors, path)
            _text(item, "meta", errors, path)

    _text(data, "languages", errors, "dados")

    contact = _mapping(data, "contact", errors, "dados")
    if contact:
        _text(contact, "intro", errors, "contact")
        items = _items(contact, "items", errors, "contact")
        for index, item in enumerate(items):
            path = f"contact.items[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{path} deve ser um objeto")
                continue
            _text(item, "label", errors, path)
            _text(item, "text", errors, path)
            if not _is_url(item.get("url")):
                errors.append(f"{path}.url deve ser uma URL http(s) ou mailto:")

    footer = _mapping(data, "footer", errors, "dados")
    if footer:
        year = footer.get("year")
        if not isinstance(year, int) or isinstance(year, bool) or year <= 0:
            errors.append("footer.year deve ser um ano inteiro positivo")
        _text(footer, "name", errors, "footer")

    return errors


def render_nav(items: list[dict[str, Any]]) -> str:
    """Renderiza os links de navegação."""
    return "\n".join(
        f'      <a href="{escape(item["href"])}">{escape(item["label"])}</a>'
        for item in items
    )


def render_hero_links(links: dict[str, Any]) -> str:
    """Renderiza GitHub, LinkedIn e e-mail do cabeçalho."""
    labels = (
        ("GitHub", "github"),
        ("LinkedIn", "linkedin"),
        ("E-mail", "email"),
    )
    return "\n".join(
        f'        <a href="{escape(links[key])}">{escape(label)}</a>'
        for label, key in labels
    )


def render_api_card(card: dict[str, Any]) -> str:
    """Renderiza o bloco que imita uma resposta de API."""
    stack = ", ".join(f'"{escape(item)}"' for item in card["stack"])
    formacao = ", ".join(f'"{escape(item)}"' for item in card["formacao"])
    return "\n".join(
        (
            '<span class="k">GET</span> <b>/joao</b>',
            f'<span class="ok">{escape(card["status"])}</span>',
            "{",
            f'  <span class="k">"cargo"</span>: "{escape(card["cargo"])}",',
            f'  <span class="k">"onde"</span>: "{escape(card["onde"])}",',
            f'  <span class="k">"stack"</span>: [{stack}],',
            f'  <span class="k">"formacao"</span>: [{formacao}],',
            f'  <span class="k">"status"</span>: "{escape(card["status_value"])}"',
            "}",
        )
    )


def render_projects(projects: list[dict[str, Any]]) -> str:
    """Renderiza a lista de projetos."""
    return "\n".join(
        "  "
        + f'<div class="proj"><h3>{escape(item["name"])}</h3>'
        + f'<p>{escape(item["description"])}</p>'
        + f'<a class="go" href="{escape(item["url"])}">{escape(item["link_label"])}</a></div>'
        for item in projects
    )


def render_tech_rows(technologies: list[dict[str, Any]]) -> str:
    """Renderiza a tabela de tecnologias."""
    return "\n".join(
        f'    <dt>{escape(item["category"])}</dt><dd>{escape(item["items"])}</dd>'
        for item in technologies
    )


def render_paragraphs(paragraphs: list[str]) -> str:
    """Renderiza parágrafos, destacando o primeiro como no layout original."""
    lines = []
    for index, text in enumerate(paragraphs):
        style = ' style="color:var(--muted)"' if index else ""
        lines.append(f"    <p{style}>{escape(text)}</p>")
    return "\n".join(lines)


def render_experience(items: list[dict[str, Any]]) -> str:
    """Renderiza a experiência profissional."""
    blocks = []
    for item in items:
        highlights = "\n".join(
            f"        <li>{escape(text)}</li>" for text in item["highlights"]
        )
        blocks.append(
            "\n".join(
                (
                    '    <div class="item">',
                    f'      <h3>{escape(item["title"])}</h3>',
                    f'      <div class="meta">{escape(item["meta"])}</div>',
                    "      <ul>",
                    highlights,
                    "      </ul>",
                    "    </div>",
                )
            )
        )
    return "\n".join(blocks)


def render_education(items: list[dict[str, Any]]) -> str:
    """Renderiza a formação acadêmica."""
    return "\n".join(
        "\n".join(
            (
                '    <div class="item">',
                f'      <h3>{escape(item["title"])}</h3>',
                f'      <div class="meta">{escape(item["meta"])}</div>',
                "    </div>",
            )
        )
        for item in items
    )


def render_contacts(items: list[dict[str, Any]]) -> str:
    """Renderiza a lista de contatos."""
    return "\n".join(
        f'    <li><a href="{escape(item["url"])}" aria-label="{escape(item["label"])}">'
        f'{escape(item["text"])}</a></li>'
        for item in items
    )


def render(data: dict[str, Any], template: str) -> str:
    """Preenche o template com os dados validados e escapados."""
    errors = validate_data(data)
    if errors:
        details = "\n".join(f"  - {error}" for error in errors)
        raise BuildError(f"Dados inválidos:\n{details}")

    owner = data["owner"]
    site = data["site"]
    values = {
        "language": escape(site.get("language", "pt-BR")),
        "title": escape(site["title"]),
        "description": escape(site["description"]),
        "keywords": escape(site.get("keywords", "Portfólio, Python, PHP")),
        "brand": escape(owner["short_name"]),
        "name": escape(owner["name"]),
        "role": escape(owner["role"]),
        "lead": escape(owner["lead"]),
        "resume": escape(owner["resume"]),
        "nav_links": render_nav(data["nav"]),
        "hero_links": render_hero_links(owner["links"]),
        "api_card": render_api_card(owner["api_card"]),
        "projects": render_projects(data["projects"]),
        "repositories_url": escape(data["repositories_url"]),
        "tech_rows": render_tech_rows(data["technologies"]),
        "about": render_paragraphs(data["about"]["paragraphs"]),
        "experience": render_experience(data["experience"]),
        "education": render_education(data["education"]),
        "languages": escape(data["languages"]),
        "contact_intro": escape(data["contact"]["intro"]),
        "contacts": render_contacts(data["contact"]["items"]),
        "year": escape(data["footer"]["year"]),
        "footer_name": escape(data["footer"]["name"]),
    }

    try:
        return string.Template(template).substitute(values)
    except KeyError as exc:
        raise BuildError(f"Placeholder sem valor no template: {exc.args[0]}") from exc
    except ValueError as exc:
        raise BuildError(f"Template inválido: {exc}") from exc


def build(
    *,
    data_path: Path = DEFAULT_DATA_PATH,
    template_path: Path = DEFAULT_TEMPLATE_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    check: bool = False,
) -> Path:
    """Gera (ou confere) o index.html na raiz do site."""
    data = load_json(data_path)
    try:
        template = template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BuildError(f"Não foi possível ler {template_path}: {exc}") from exc

    generated = render(data, template).rstrip("\n") + "\n"

    if check:
        try:
            current = output_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise BuildError(f"Não foi possível ler {output_path}: {exc}") from exc
        if current != generated:
            raise BuildError(f"{output_path} está desatualizado. Execute: python build.py")
        return output_path

    try:
        with output_path.open("w", encoding="utf-8", newline="\n") as output:
            output.write(generated)
    except OSError as exc:
        raise BuildError(f"Não foi possível escrever {output_path}: {exc}") from exc
    return output_path


def main(argv: list[str] | None = None) -> int:
    """Executa a interface de linha de comando do build."""
    parser = argparse.ArgumentParser(
        description="Gera o index.html do portfólio a partir de site/data.json."
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--check",
        action="store_true",
        help="confere se o index.html está atualizado sem sobrescrevê-lo",
    )
    args = parser.parse_args(argv)

    try:
        path = build(
            data_path=args.data,
            template_path=args.template,
            output_path=args.output,
            check=args.check,
        )
    except BuildError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    action = "atualizado" if args.check else "gerado"
    print(f"Site {action}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
