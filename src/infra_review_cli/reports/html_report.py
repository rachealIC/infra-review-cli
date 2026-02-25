from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


def _load_static(filename: str) -> str:
    """Reads a static file's content from the static directory."""
    return (STATIC_DIR / filename).read_text(encoding="utf-8")


def render_html_report(data: dict) -> str:
    """
    Renders a self-contained HTML report by:
      1. Loading CSS and JS from static source files
      2. Injecting them inline into the Jinja2 template
      3. Returning the final single-file HTML string

    The output file has zero external dependencies —
    CSS and JS are inlined so the report can be emailed
    or shared without broken asset links.

    Args:
        data: dict with keys matching template variables

    Returns:
        The rendered HTML content as a string
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )

    template = env.get_template("report.html.j2")

    # Inject static assets into the render context
    html = template.render(
        **data,
        inline_css=_load_static("report.css"),
        inline_js=_load_static("report.js"),
    )

    return html
