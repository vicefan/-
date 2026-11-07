from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import HEADERS

URL = (
    "https://job.inha.ac.kr/Community/Program/ProgramList.aspx?"
    "prodiv=99&rp=1"
)


def scrape_jobs(url: str = URL) -> list[dict[str, str]]:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.select("div.prod-list")
    if not rows:
        raise RuntimeError("인하대학교 취업 프로그램 목록을 찾지 못했습니다.")

    jobs = []
    for row in rows:
        row_text = row.get_text(" ", strip=True)

        if "마감" in row_text:
            continue

        title = row.select_one("div.prod1")
        department = row.select_one("div.prod2-1")
        application_period = row.select_one("div[id$='_DateTime_txt']")
        education_period = row.select_one("div[id$='_eduArea']")
        onclick = row.parent.get("onclick", "")

        if not all((title, department, application_period, education_period)):
            continue

        prefix = "javascript:goView('"
        suffix = "')"
        program_id = (
            onclick[len(prefix) : -len(suffix)]
            if onclick.startswith(prefix) and onclick.endswith(suffix)
            else ""
        )
        if not program_id:
            continue

        jobs.append(
            {
                "title": title.get_text(" ", strip=True),
                "link": urljoin(
                    url,
                    f"/community/Program/programView.aspx?pgdx={program_id}",
                ),
                "department": department.get_text(" ", strip=True),
                "application_period": application_period.get_text(
                    " ", strip=True
                ),
                "education_period": education_period.get_text(" ", strip=True),
                "description": row_text,
            }
        )

    return jobs


if __name__ == "__main__":
    job_list = scrape_jobs()
    print(f"총 {len(job_list)}개의 취업 프로그램을 찾았습니다.\n")
    for job in job_list:
        print(job)
        print()
