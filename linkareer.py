from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import HEADERS, is_target_job

URL = (
    "https://linkareer.com/list/intern?filterBy_activityTypeID=5"
    "&filterBy_categoryIDs=110004&filterBy_categoryIDs=110003"
    "&filterBy_categoryIDs=110002&filterBy_internTypeIds=1"
    "&filterBy_jobTypes=INTERN&filterBy_regionIDs=2&filterBy_regionIDs=5"
    "&filterBy_status=OPEN&orderBy_direction=DESC&orderBy_field=RECENT&page=1"
)


def scrape_jobs(url: str = URL) -> list[dict[str, str]]:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.select("tr[data-activityid]")
    if not rows:
        raise RuntimeError("링커리어 채용 공고 목록을 찾지 못했습니다.")

    jobs = []
    for row in rows:
        if not is_target_job(row.get_text(" ", strip=True)):
            continue

        company = row.select_one("p.company-name")
        title = row.select_one("p.recruit-name")
        link = row.select_one("a.recruit-link")
        category = row.select_one("p.recruit-category")
        employment_type = row.select_one("div.item-recruit-type p")
        location = row.select_one("div.item-location p")
        deadline = row.select_one("div.item-recruit-close p")

        if not all((company, title, link, category, employment_type, location, deadline)):
            continue

        jobs.append(
            {
                "company": company.get_text(" ", strip=True),
                "title": title.get_text(" ", strip=True),
                "link": urljoin(url, link["href"]),
                "description": category.get_text(" ", strip=True),
                "employment": employment_type.get_text(" ", strip=True),
                "work_place": location.get_text(" ", strip=True),
                "deadline": deadline.get_text(" ", strip=True),
            }
        )

    return jobs


if __name__ == "__main__":
    job_list = scrape_jobs()
    print(f"총 {len(job_list)}개의 채용 공고를 찾았습니다.\n")
    for job in job_list:
        print(job)
        print()
