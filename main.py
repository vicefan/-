import html
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

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
PROGRAM_SOURCES = {"인하대학교"}


def get_job_key(job: dict[str, str]) -> str:
    """Return a stable identity, ignoring tracking parameters and URL casing."""
    source = job.get("source", "")
    parts = urlsplit(job.get("link", ""))
    if source == "인하대학교":
        program_id = parse_qs(parts.query).get("pgdx", [""])[0]
        if program_id:
            return f"{source}:program:{program_id}"

    kept_query = [
        (key, value)
        for key, values in parse_qs(parts.query, keep_blank_values=True).items()
        if key not in {"adsCategoryItem", "adsCategoryItemNo", "search"}
        for value in values
    ]
    canonical_link = urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, urlencode(kept_query), "")
    )
    return f"{source}:link:{canonical_link}"


def create_database() -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_jobs (
                link TEXT PRIMARY KEY,
                job_key TEXT,
                first_seen_at TEXT NOT NULL,
                job_json TEXT
            )
            """
        )
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(seen_jobs)")
        }
        if "job_json" not in columns:
            connection.execute("ALTER TABLE seen_jobs ADD COLUMN job_json TEXT")
        if "job_key" not in columns:
            connection.execute("ALTER TABLE seen_jobs ADD COLUMN job_key TEXT")

        rows = connection.execute(
            "SELECT rowid, link, job_json FROM seen_jobs"
        ).fetchall()
        for rowid, link, job_json in rows:
            job = json.loads(job_json) if job_json else {"link": link}
            connection.execute(
                "UPDATE seen_jobs SET job_key = ? WHERE rowid = ?",
                (get_job_key(job), rowid),
            )
        connection.execute(
            """
            DELETE FROM seen_jobs
            WHERE rowid NOT IN (
                SELECT MAX(rowid) FROM seen_jobs GROUP BY job_key
            )
            """
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_seen_jobs_job_key "
            "ON seen_jobs(job_key)"
        )


def get_new_jobs(
    jobs: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    unique_jobs = {
        get_job_key(job): job for job in jobs if job.get("link")
    }
    with sqlite3.connect(DATABASE_PATH) as connection:
        seen_links = {
            row[0]
            for row in connection.execute(
                "SELECT job_key FROM seen_jobs WHERE job_key IN ({})".format(
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
            """
            INSERT INTO seen_jobs (link, job_key, first_seen_at, job_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(job_key) DO UPDATE SET
                link = excluded.link,
                job_json = excluded.job_json
            """,
            (
                (
                    job["link"],
                    get_job_key(job),
                    now,
                    json.dumps(job, ensure_ascii=False),
                )
                for job in unique_jobs.values()
            ),
        )
        all_jobs = []
        for link, first_seen_at, job_json in connection.execute(
            "SELECT link, first_seen_at, job_json FROM seen_jobs "
            "ORDER BY first_seen_at DESC"
        ):
            job = json.loads(job_json) if job_json else {
                "link": link,
                "title": "기존 공고",
                "company": "",
            }
            job["first_seen_at"] = first_seen_at
            all_jobs.append(job)
    return new_jobs, all_jobs


def render_html(
    new_jobs: list[dict[str, str]],
    all_jobs: list[dict[str, str]],
    errors: list[str],
) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def render_cards(jobs: list[dict[str, str]], empty_message: str) -> str:
        cards = []
        for job in jobs:
            category = (
                "취업 프로그램"
                if job.get("source") in PROGRAM_SOURCES
                else "채용 공고"
            )
            job_key = html.escape(get_job_key(job), quote=True)
            details = [
                f"<strong>{html.escape(key)}:</strong> {html.escape(value)}"
                for key, value in job.items()
                if key not in {
                    "link", "title", "company", "source", "first_seen_at"
                } and value
            ]
            cards.append(
                f"""
                <article class="card" data-source="{html.escape(job.get("source", ""), quote=True)}"
                  data-category="{category}" data-job-key="{job_key}">
                  <p class="source">{html.escape(job.get("source", ""))}</p>
                  <h2><a href="{html.escape(job["link"], quote=True)}" target="_blank">
                    {html.escape(job.get("title", "제목 없음"))}
                  </a></h2>
                  <p class="company">{html.escape(job.get("company", ""))}</p>
                  <div class="details">{"<br>".join(details)}</div>
                  <button class="dislike-button" type="button">별로예요</button>
                </article>
                """.strip()
            )
        return "\n".join(cards) or f'<p class="empty">{html.escape(empty_message)}</p>'

    new_cards = render_cards(new_jobs, "새로 추가된 공고가 없습니다.")
    all_cards = render_cards(all_jobs, "저장된 공고가 없습니다.")
    error_html = "".join(f"<li>{html.escape(error)}</li>" for error in errors)

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>채용 공고</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f3f5f7; color: #202124;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    header {{ padding: 24px 16px 12px; max-width: 760px; margin: auto; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    .generated {{ color: #687078; font-size: 13px; }}
    .tabs {{ display: flex; gap: 8px; margin-top: 16px; }}
    .tab {{ border: 0; border-radius: 8px; padding: 10px 14px; background: #dfe3e8;
            color: #3c4650; cursor: pointer; font-size: 14px; }}
    .tab.active {{ background: #5271ff; color: white; }}
    .tab-panel {{ display: none; }}
    .tab-panel.active {{ display: block; }}
    .filters {{ background: white; border-radius: 12px; padding: 14px 16px;
                margin: 16px 0; box-shadow: 0 1px 5px #00000012; }}
    .filter-title {{ font-weight: 700; margin: 0 0 10px; }}
    .filter-options {{ display: flex; flex-wrap: wrap; gap: 8px 14px; }}
    .filter-options label {{ font-size: 14px; cursor: pointer; }}
    .filter-options input {{ margin-right: 4px; }}
    .filter-actions {{ display: flex; gap: 8px; margin-top: 12px; }}
    .filter-actions button, .dislike-button {{ border: 1px solid #c9ced6; border-radius: 6px;
      padding: 6px 10px; background: white; color: #3c4650; cursor: pointer; }}
    .card.hidden-by-filter, .card.disliked {{ display: none; }}
    .card.is-disliked {{ opacity: .58; }}
    .card.is-disliked .dislike-button {{ background: #ffe4e4; border-color: #e19a9a; }}
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
    <h1>채용 공고</h1>
    <div class="generated">생성 시각: {generated_at}</div>
    <nav class="tabs" aria-label="공고 보기">
      <button class="tab active" type="button" data-tab="new">새 공고 ({len(new_jobs)}개)</button>
      <button class="tab" type="button" data-tab="all">전체 공고 ({len(all_jobs)}개)</button>
    </nav>
    <div class="filters" aria-label="공고 필터">
      <p class="filter-title">분류</p>
      <div class="filter-options">
        <label><input type="checkbox" name="category" value="채용 공고" checked> 채용 공고</label>
        <label><input type="checkbox" name="category" value="취업 프로그램" checked> 취업 프로그램</label>
      </div>
      <p class="filter-title">사이트</p>
      <div class="filter-options">
        {''.join(
            f'<label><input type="checkbox" name="source" value="{html.escape(source, quote=True)}" checked> '
            f'{html.escape(source)}</label>'
            for source in SCRAPERS
        )}
      </div>
      <div class="filter-actions">
        <button id="select-all" type="button">전체 선택</button>
        <button id="clear-all" type="button">전체 해제</button>
        <label><input id="show-disliked" type="checkbox"> 별로예요 표시 보기</label>
      </div>
    </div>
    {"<ul class='errors'>" + error_html + "</ul>" if errors else ""}
  </header>
  <main>
    <section id="new" class="tab-panel active">{new_cards}</section>
    <section id="all" class="tab-panel">{all_cards}</section>
  </main>
  <script>
    const cards = [...document.querySelectorAll(".card")];
    const filters = [...document.querySelectorAll(
      'input[name="category"], input[name="source"]'
    )];
    const dislikedStorageKey = "job-page-disliked";
    const disliked = new Set(JSON.parse(
      localStorage.getItem(dislikedStorageKey) || "[]"
    ));

    function updateCards() {{
      const categories = new Set(filters.filter((input) =>
        input.checked && input.name === "category").map((input) => input.value));
      const sources = new Set(filters.filter((input) =>
        input.checked && input.name === "source").map((input) => input.value));
      const showDisliked = document.querySelector("#show-disliked").checked;
      cards.forEach((card) => {{
        const isDisliked = disliked.has(card.dataset.jobKey);
        card.classList.toggle("is-disliked", isDisliked);
        card.classList.toggle("hidden-by-filter",
          !categories.has(card.dataset.category) ||
          !sources.has(card.dataset.source) ||
          (isDisliked && !showDisliked));
      }});
    }}

    cards.forEach((card) => {{
      const button = card.querySelector(".dislike-button");
      button.addEventListener("click", () => {{
        const key = card.dataset.jobKey;
        if (disliked.has(key)) {{
          disliked.delete(key);
        }} else {{
          disliked.add(key);
        }}
        localStorage.setItem(dislikedStorageKey, JSON.stringify([...disliked]));
        updateCards();
      }});
    }});
    filters.forEach((input) => input.addEventListener("change", updateCards));
    document.querySelector("#show-disliked").addEventListener("change", updateCards);
    document.querySelector("#select-all").addEventListener("click", () => {{
      filters.forEach((input) => input.checked = true);
      updateCards();
    }});
    document.querySelector("#clear-all").addEventListener("click", () => {{
      filters.forEach((input) => input.checked = false);
      updateCards();
    }});

    document.querySelectorAll(".tab").forEach((button) => {{
      button.addEventListener("click", () => {{
        document.querySelectorAll(".tab, .tab-panel").forEach((element) => {{
          element.classList.toggle("active", element === button ||
            element.id === button.dataset.tab);
        }});
      }});
    }});
    updateCards();
  </script>
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

    new_jobs, all_jobs = get_new_jobs(jobs)
    HTML_PATH.write_text(
        render_html(new_jobs, all_jobs, errors), encoding="utf-8"
    )
    print(f"전체 수집: {len(jobs)}개")
    print(f"새 공고: {len(new_jobs)}개")
    print(f"HTML 저장: {HTML_PATH}")
    if errors:
        print("실패한 사이트:")
        print("\n".join(f"- {error}" for error in errors))


if __name__ == "__main__":
    main()