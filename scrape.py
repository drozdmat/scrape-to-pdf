#!/usr/bin/env python3
"""Scrape 'The Toughest Sell' from derekyan.com and produce a single PDF."""

import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from weasyprint import HTML

BASE_URL = "https://derekyan.com/ma-book"

PAGES = (
    ["foreword.html"]
    + [f"chapter-{i}.html" for i in range(1, 54)]
    + ["epilogue.html"]
)


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    })
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def fetch_page(session: requests.Session, slug: str) -> BeautifulSoup:
    url = f"{BASE_URL}/{slug}"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def extract_chapter(soup: BeautifulSoup) -> dict:
    """Return structured data from a chapter page."""
    article = soup.find("article", class_="chapter-content")

    header = article.find("div", class_="chapter-header")
    part_label_el = header.find("span", class_="part-label") if header else None
    part_label = part_label_el.get_text(strip=True) if part_label_el else None

    h1 = header.find("h1") if header else soup.find("h1")
    chapter_num_el = h1.find("span", class_="chapter-number") if h1 else None
    chapter_number = chapter_num_el.get_text(strip=True) if chapter_num_el else None
    # Title is the remaining text after the chapter-number span
    if chapter_num_el:
        chapter_num_el.extract()
    title = h1.get_text(strip=True) if h1 else ""

    body = article.find("div", class_="chapter-body")
    body_html = body.decode_contents() if body else ""

    return {
        "part": part_label,
        "chapter_number": chapter_number,
        "title": title,
        "body_html": body_html,
    }


def build_html(chapters: list[dict]) -> str:
    """Build a single HTML document from all scraped chapters."""
    chapter_blocks = []
    current_part = None

    for ch in chapters:
        # Insert a part divider page when the part changes
        if ch["part"] and ch["part"] != current_part:
            current_part = ch["part"]
            chapter_blocks.append(
                f'<div class="part-divider"><h2>{current_part}</h2></div>'
            )

        # Chapter heading
        if ch["chapter_number"]:
            heading = f'{ch["chapter_number"]} &mdash; {ch["title"]}'
        else:
            heading = ch["title"]

        chapter_blocks.append(
            f'<div class="chapter">'
            f"<h3>{heading}</h3>"
            f'<div class="body">{ch["body_html"]}</div>'
            f"</div>"
        )

    content = "\n".join(chapter_blocks)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4;
    margin: 2.5cm 2cm;
    @bottom-center {{
      content: counter(page);
      font-size: 9pt;
      color: #666;
    }}
  }}
  body {{
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #222;
  }}

  /* ---- Title page ---- */
  .title-page {{
    page-break-after: always;
    text-align: center;
    padding-top: 30%;
  }}
  .title-page h1 {{
    font-size: 28pt;
    margin-bottom: 0.3em;
  }}
  .title-page .subtitle {{
    font-size: 14pt;
    color: #555;
    margin-bottom: 2em;
  }}
  .title-page .author {{
    font-size: 13pt;
    color: #444;
  }}

  /* ---- Part dividers ---- */
  .part-divider {{
    page-break-before: always;
    page-break-after: always;
    text-align: center;
    padding-top: 40%;
  }}
  .part-divider h2 {{
    font-size: 22pt;
    color: #333;
    border-bottom: 2px solid #999;
    display: inline-block;
    padding-bottom: 0.3em;
  }}

  /* ---- Chapters ---- */
  .chapter {{
    page-break-before: always;
  }}
  .chapter h3 {{
    font-size: 16pt;
    margin-bottom: 1em;
    color: #111;
  }}
  .chapter .body {{
    text-align: justify;
  }}
  .chapter .body p {{
    margin-bottom: 0.8em;
    text-indent: 0;
  }}
</style>
</head>
<body>

<div class="title-page">
  <h1>The Toughest Sell</h1>
  <div class="subtitle">A Founder&rsquo;s Guide to Startup Exits</div>
  <div class="author">Derek Z. H. Yan</div>
</div>

{content}

</body>
</html>"""


def main():
    session = make_session()
    chapters = []
    total = len(PAGES)

    for i, slug in enumerate(PAGES, 1):
        print(f"[{i}/{total}] Fetching {slug} ...")
        soup = fetch_page(session, slug)
        ch = extract_chapter(soup)
        chapters.append(ch)
        time.sleep(0.5)

    print("Building PDF ...")
    html_str = build_html(chapters)
    HTML(string=html_str).write_pdf("the_toughest_sell.pdf")
    print("Done → the_toughest_sell.pdf")


if __name__ == "__main__":
    main()
