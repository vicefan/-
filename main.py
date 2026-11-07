import html
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Callable

from incheon import scrape_jobs as scrape_incheon
from jasoseol import scrape_jobs as scrape_jasoseol
from jobinha import scrape_jobs as scrape_jobinha
from jobkorea import scrape_jobs as scrape_jobkorea
from linkareer import scrape_jobs as scrape_linkareer
from saramin import scrape_jobs as scrape_saramin

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "jobs.sqlite3"
HTML_PATH = BASE_DIR / "jobs.html"

Scraper = Callable[[], list[dict[str, str]]]
SCRAPERS: dict[str, Scraper] = {
    "잡코리아": scrape_jobkorea,
    "사람인": scrape_saramin,
    "자소설닷컴": scrape_jasoseol,
    "링커리어": scrape_linkareer,
    "인천일자리포털": scrape_incheon,
    "인하대학교": scrape_jobinha,
}


def create_database() -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_jobs (
                link TEXT PRIMARY KEY,
                first_seen_at TEXT NOT NULL
            )
            """
        )


def get_new_jobs(jobs: list[dict[str, str]]) -> list[dict[str, str]]:
    unique_jobs = {job["link"]: job for job in jobs if job.get("link")}
    with sqlite3.connect(DATABASE_PATH) as connection:
        seen_links = {
            row[0]
            for row in connection.execute(
                "SELECT link FROM seen_jobs WHERE link IN ({})".format(
                    ",".join("?" for _ in unique_jobs) or "NULL"
                ),
                tuple(unique_jobs),
            )
        }
        new_jobs = [
            job for link, job in unique_jobs.items() if link not in seen_links
        ]
        now = datetime.now().isoformat(timespec="seconds")
        connection.executemany(
            "INSERT OR IGNORE INTO seen_jobs (link, first_seen_at) VALUES (?, ?)",
            ((job["link"], now) for job in unique_jobs.values()),
        )
    return new_jobs


def render_html(jobs: list[dict[str, str]], errors: list[str]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cards = []
    for job in jobs:
        details = [
            f"<strong>{html.escape(key)}:</strong> {html.escape(value)}"
            for key, value in job.items()
            if key not in {"link", "title", "company", "source"} and value
        ]
        cards.append(
            f"""
            <article class="card">
              <p class="source">{html.escape(job.get("source", ""))}</p>
              <h2><a href="{html.escape(job["link"], quote=True)}" target="_blank">
                {html.escape(job.get("title", "제목 없음"))}
              </a></h2>
              <p class="company">{html.escape(job.get("company", ""))}</p>
              <div class="details">{"<br>".join(details)}</div>
            </article>
            """
        )

    error_html = "".join(f"<li>{html.escape(error)}</li>" for error in errors)
    if not cards:
        cards = ["<p class=\"empty\">새로 추가된 공고가 없습니다.</p>"]

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>새 채용 공고</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f3f5f7; color: #202124;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    header {{ padding: 24px 16px 12px; max-width: 760px; margin: auto; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    .generated {{ color: #687078; font-size: 13px; }}
    main {{ max-width: 760px; margin: auto; padding: 8px 16px 32px; }}
    .card {{ background: white; border-radius: 12px; padding: 16px;
             margin: 12px 0; box-shadow: 0 1px 5px #00000012; }}
    .source {{ color: #5271ff; font-size: 13px; font-weight: 700; margin: 0 0 8px; }}
    h2 {{ font-size: 18px; line-height: 1.4; margin: 0 0 6px; }}
    a {{ color: #172b4d; text-decoration: none; }}
    .company {{ margin: 0 0 12px; color: #444; }}
    .details {{ color: #59636e; font-size: 14px; line-height: 1.7; }}
    .empty {{ text-align: center; padding: 40px 0; color: #687078; }}
    .errors {{ color: #a33; font-size: 13px; }}
  </style>
</head>
<body>
  <header>
    <h1>새 채용 공고 ({len(jobs)}개)</h1>
    <div class="generated">생성 시각: {generated_at}</div>
    {"<ul class='errors'>" + error_html + "</ul>" if errors else ""}
  </header>
  <main>{"".join(cards)}</main>
</body>
</html>
"""


def main() -> None:
    create_database()
    jobs: list[dict[str, str]] = []
    errors = []
    for source, scraper in SCRAPERS.items():
        try:
            for job in scraper():
                job["source"] = source
                jobs.append(job)
        except Exception as error:
            errors.append(f"{source}: {type(error).__name__}: {error}")

    new_jobs = get_new_jobs(jobs)
    HTML_PATH.write_text(render_html(new_jobs, errors), encoding="utf-8")
    print(f"전체 수집: {len(jobs)}개")
    print(f"새 공고: {len(new_jobs)}개")
    print(f"HTML 저장: {HTML_PATH}")
    if errors:
        print("실패한 사이트:")
        print("\n".join(f"- {error}" for error in errors))


if __name__ == "__main__":
    main()