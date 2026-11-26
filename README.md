# Portfólio — João Marcelo

Portfólio estático de **João Marcelo Neves de Lima**, engenheiro de software e desenvolvedor back-end. O site publicado no GitHub Pages é gerado a partir de dados em JSON e de um template HTML, usando apenas a biblioteca padrão do Python.

O currículo [`curriculo-joao-marcelo.pdf`](curriculo-joao-marcelo.pdf) faz parte do site e é mantido sem alterações pelo gerador.

## Tecnologias

- **Python 3.15** (compatível com 3.13) — leitura de JSON, validação, escape e renderização com `string.Template`.
- **HTML5 e CSS3** — layout responsivo, sem frameworks de front-end e sem JavaScript.
- **GitHub Pages** — publicação do `index.html` na raiz do repositório.
- **Docker** — build reproduce o ambiente Python 3.15 em qualquer máquina.
- **GitHub Actions** — testes, checagem do HTML versionado e upload do site como artifact.
- **`unittest`** — testes embutidos na biblioteca padrão, sem `pip install`.

Stack apresentada no portfólio: **PHP/Laravel, C#, Python, Docker, APIs, IoT, MySQL e .NET**.

## Pré-requisitos

- Python 3.13 ou 3.15 (testado nas duas versões na CI).
- Opcional: Docker para gerar o site sem instalar Python localmente.
- Não há dependências externas: nada de `requirements.txt` nem `pip install`.

## Estrutura

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml                 # Testes, build e artifact
├── site/
│   ├── data.json                  # Conteúdo do portfólio (textos, links, projetos)
│   └── template.html              # Layout com placeholders $nome
├── tests/
│   └── test_build.py              # Testes unittest do gerador
├── build.py                       # CLI que gera index.html na raiz
├── index.html                     # Site versionado, servido pelo GitHub Pages
├── curriculo-joao-marcelo.pdf     # Currículo (preservado)
├── Dockerfile                     # Build em Python 3.15-slim
└── README.md
```

## Como funciona

```text
site/data.json ──► build.py ──► index.html ──► GitHub Pages
site/template.html     │
                       └── string.Template + html.escape
```

`build.py` valida os dados (campos obrigatórios, URLs http(s)/mailto, PDF relativo), escapa todos os valores dinâmicos e preenche o template. Se algum campo estiver ausente ou inseguro, o comando termina com uma mensagem clara e não sobrescreve o HTML.

## Build

Na raiz do repositório:

```bash
python build.py
```

Saída esperada:

```text
Site gerado: .../index.html
```

Opções úteis:

```bash
# Confere se o index.html versionado está atualizado, sem alterá-lo
python build.py --check

# Usa arquivos alternativos (útil em scripts ou testes)
python build.py --data site/data.json --template site/template.html --output index.html
```

Com Docker:

```bash
docker build -t portifolio-jneves07 .
docker run --rm -v "$PWD:/app" portifolio-jneves07
```

O volume montado faz o `index.html` gerado aparecer na pasta atual.

## Preview local

Depois do build, sirva a pasta na porta 8000:

```bash
python -m http.server 8000
```

Acesse <http://localhost:8000>. O nome da pasta não importa: o servidor serve `index.html` e o PDF a partir da raiz.

## Testes

```bash
python -m unittest discover -s tests -v
```

A suíte verifica que o HTML gerado contém nome, seções, tecnologias, link do currículo e links dos repositórios, que o `index.html` versionado está idempotente, que dados inválidos e JSON corrompido geram erros amigáveis e que placeholders ausentes são reportados.

## CI

`.github/workflows/ci.yml` executa em *push* na branch `main`, em *pull requests* e manualmente:

1. testes com `python -m unittest discover -s tests -v`;
2. `python build.py --check` para garantir que o HTML commitado corresponde aos dados;
3. `python build.py` para gerar o site;
4. upload de `index.html` como artifact `portfolio-index`.

A matriz roda no Python 3.13 e 3.15. Não há segredos no repositório.

## Personalização

Edite apenas `site/data.json` para alterar textos, projetos, tecnologias e links. Depois rode `python build.py` e commite o `index.html` resultante. Para mudar o visual, edite `site/template.html` mantendo os placeholders `$...` utilizados em `build.py`.
