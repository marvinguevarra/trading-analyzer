"""Sync project docs to Confluence on every push.

Pushes CLAUDE.md and CHANGELOG.md (and any other registered docs) to
Confluence pages in the PM space. Creates pages if they don't exist,
updates if they do.

Usage:
    python3 scripts/confluence_sync.py                  # sync all registered docs
    python3 scripts/confluence_sync.py CLAUDE.md        # sync one file
    python3 scripts/confluence_sync.py --snippet FILE TITLE  # push any file as a page

Credentials read from .env (CONFLUENCE_URL, CONFLUENCE_EMAIL,
CONFLUENCE_API_TOKEN, CONFLUENCE_SPACE).
"""

import argparse
import base64
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# ── Docs to sync automatically ──
# Format: (local_path_relative_to_root, confluence_page_title)
REGISTERED_DOCS = [
    ("CLAUDE.md", "Trading Analyzer — CLAUDE.md"),
    ("CHANGELOG.md", "Trading Analyzer — CHANGELOG"),
]


def _load_env() -> dict[str, str]:
    """Load .env from project root."""
    env: dict[str, str] = {}
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        print("No .env file found. Skipping Confluence sync.", file=sys.stderr)
        sys.exit(0)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    required = ["CONFLUENCE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN", "CONFLUENCE_SPACE"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        print(f"Missing env vars: {missing}. Skipping Confluence sync.", file=sys.stderr)
        sys.exit(0)
    return env


def _headers(env: dict[str, str]) -> dict[str, str]:
    creds = base64.b64encode(
        f"{env['CONFLUENCE_EMAIL']}:{env['CONFLUENCE_API_TOKEN']}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {creds}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _get_space_id(env: dict[str, str]) -> str:
    """Resolve space key to space ID."""
    space_key = env["CONFLUENCE_SPACE"]
    url = f"https://{env['CONFLUENCE_URL']}/wiki/api/v2/spaces?keys={space_key}"
    req = urllib.request.Request(url, headers=_headers(env))
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    return data["results"][0]["id"]


def md_to_confluence(md_text: str) -> str:
    """Convert Markdown to Confluence storage format HTML.

    Handles: headings, code blocks (with language), tables, bold, italic,
    inline code, links, lists, horizontal rules, and plain paragraphs.
    """
    lines = md_text.split("\n")
    out: list[str] = []
    in_code = False
    code_lang = ""
    code_buf: list[str] = []
    in_table = False
    in_list = False

    def _inline(text: str) -> str:
        """Process inline formatting: bold, italic, code, links."""
        # Inline code (before other processing to protect contents)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        # Bold
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        # Italic
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        # Links [text](url)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        return text

    for line in lines:
        # ── Code blocks ──
        if line.startswith("```"):
            if in_code:
                raw = "\n".join(code_buf)
                lang_attr = f' ac:name="language"><ac:parameter ac:name="language">{code_lang}</ac:parameter' if code_lang else ' ac:name="code"'
                if code_lang:
                    out.append(
                        f'<ac:structured-macro ac:name="code">'
                        f'<ac:parameter ac:name="language">{html.escape(code_lang)}</ac:parameter>'
                        f"<ac:plain-text-body><![CDATA[{raw}]]></ac:plain-text-body>"
                        f"</ac:structured-macro>"
                    )
                else:
                    out.append(
                        f'<ac:structured-macro ac:name="code">'
                        f"<ac:plain-text-body><![CDATA[{raw}]]></ac:plain-text-body>"
                        f"</ac:structured-macro>"
                    )
                code_buf = []
                code_lang = ""
                in_code = False
            else:
                in_code = True
                code_lang = line[3:].strip()
            continue

        if in_code:
            code_buf.append(line)
            continue

        # ── Close open list if needed ──
        if in_list and not line.startswith("- ") and not line.startswith("  -"):
            out.append("</ul>")
            in_list = False

        # ── Headings ──
        if line.startswith("#### "):
            out.append(f"<h4>{_inline(html.escape(line[5:]))}</h4>")
        elif line.startswith("### "):
            out.append(f"<h3>{_inline(html.escape(line[4:]))}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{_inline(html.escape(line[3:]))}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{_inline(html.escape(line[2:]))}</h1>")

        # ── Horizontal rule ──
        elif line.strip() == "---":
            if in_table:
                out.append("</tbody></table>")
                in_table = False
            out.append("<hr/>")

        # ── Tables ──
        elif "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # Skip separator rows (---|---)
            if all(set(c.strip()) <= set("- :") for c in cells):
                continue
            if not in_table:
                out.append("<table><tbody>")
                in_table = True
                out.append(
                    "<tr>"
                    + "".join(f"<th>{_inline(html.escape(c))}</th>" for c in cells)
                    + "</tr>"
                )
            else:
                out.append(
                    "<tr>"
                    + "".join(f"<td>{_inline(html.escape(c))}</td>" for c in cells)
                    + "</tr>"
                )

        # ── List items ──
        elif line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_inline(html.escape(line[2:]))}</li>")

        # ── Blank lines ──
        elif line.strip() == "":
            if in_table:
                out.append("</tbody></table>")
                in_table = False

        # ── Plain paragraph ──
        else:
            if in_table:
                out.append("</tbody></table>")
                in_table = False
            out.append(f"<p>{_inline(html.escape(line))}</p>")

    # Close any open elements
    if in_table:
        out.append("</tbody></table>")
    if in_list:
        out.append("</ul>")

    return "\n".join(out)


def sync_page(env: dict[str, str], space_id: str, title: str, md_content: str) -> str:
    """Create or update a Confluence page. Returns the page URL."""
    hdrs = _headers(env)
    base = f"https://{env['CONFLUENCE_URL']}"

    # Check if page exists
    search_url = (
        f"{base}/wiki/api/v2/spaces/{space_id}/pages"
        f"?title={urllib.parse.quote(title)}"
    )
    req = urllib.request.Request(search_url, headers=hdrs)
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())

    body_html = md_to_confluence(md_content)

    if data.get("results"):
        # Update existing page
        page = data["results"][0]
        page_id = page["id"]
        version = page["version"]["number"] + 1

        payload = json.dumps({
            "id": page_id,
            "status": "current",
            "title": title,
            "body": {"representation": "storage", "value": body_html},
            "version": {"number": version},
        }).encode()

        req = urllib.request.Request(
            f"{base}/wiki/api/v2/pages/{page_id}",
            data=payload, headers=hdrs, method="PUT",
        )
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        webui = result.get("_links", {}).get("webui", "")
        page_url = f"{base}/wiki{webui}"
        print(f"  Updated: {title} (v{version}) -> {page_url}")
        return page_url
    else:
        # Create new page
        payload = json.dumps({
            "spaceId": space_id,
            "status": "current",
            "title": title,
            "body": {"representation": "storage", "value": body_html},
        }).encode()

        req = urllib.request.Request(
            f"{base}/wiki/api/v2/pages",
            data=payload, headers=hdrs, method="POST",
        )
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        webui = result.get("_links", {}).get("webui", "")
        page_url = f"{base}/wiki{webui}"
        print(f"  Created: {title} -> {page_url}")
        return page_url


def sync_all(env: dict[str, str], space_id: str) -> None:
    """Sync all registered docs."""
    print("Syncing to Confluence...")
    for rel_path, title in REGISTERED_DOCS:
        file_path = PROJECT_ROOT / rel_path
        if not file_path.exists():
            print(f"  Skipped: {rel_path} (not found)")
            continue
        content = file_path.read_text()
        sync_page(env, space_id, title, content)
    print("Done.")


def sync_snippet(env: dict[str, str], space_id: str, file_path: str, title: str) -> None:
    """Push any file as a Confluence page (code snippet, doc, etc.)."""
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    content = path.read_text()
    suffix = path.suffix.lstrip(".")

    # Wrap code files in a code block
    code_extensions = {"py", "js", "ts", "tsx", "json", "yaml", "yml", "toml", "sh", "bash", "sql", "html", "css"}
    if suffix in code_extensions:
        md_content = f"# {title}\n\nSource: `{path.name}`\n\n```{suffix}\n{content}\n```"
    else:
        md_content = content

    print(f"Pushing snippet: {path.name} -> '{title}'")
    sync_page(env, space_id, f"Trading Analyzer — {title}", md_content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync docs to Confluence")
    parser.add_argument("file", nargs="?", help="Specific file to sync (e.g. CLAUDE.md)")
    parser.add_argument("--snippet", nargs=2, metavar=("FILE", "TITLE"),
                        help="Push any file as a Confluence page")
    args = parser.parse_args()

    env = _load_env()
    space_id = _get_space_id(env)

    if args.snippet:
        sync_snippet(env, space_id, args.snippet[0], args.snippet[1])
    elif args.file:
        # Find in registered docs
        match = [(p, t) for p, t in REGISTERED_DOCS if args.file in p]
        if match:
            rel_path, title = match[0]
            content = (PROJECT_ROOT / rel_path).read_text()
            sync_page(env, space_id, title, content)
        else:
            # Treat as snippet
            sync_snippet(env, space_id, args.file, Path(args.file).stem)
    else:
        sync_all(env, space_id)
