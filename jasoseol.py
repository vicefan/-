from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import HEADERS, is_target_job

URL = (
    "https://jasoseol.com/search?"
    "division=3&dutyGroupIds=150%2C151%2C152%2C157%2C158&excludeClosed=true"
)


def scrape_jobs(url: str = URL) -> list[dict[str, str]]:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    cards = soup.select("a.block[href^='/recruit/']")
    if not cards:
        raise RuntimeError("자소설닷컴 채용 공고 목록을 찾지 못했습니다.")

    jobs = []
    for card in cards:
        if not is_target_job(card.get_text(" ", strip=True)):
            continue

        company = card.select_one("h5")
        title = card.select_one("h4")
        position = card.select_one("div.body5")
        employment_type = card.select_one(
            "[data-sentry-component='CompanyEmploymentType']"
        )
        period = card.select_one(
            "[data-sentry-component='EmploymentPeriod'] div.body6"
        )
        d_day = card.select_one("[data-sentry-component='RecruitDDay']")

        if not all((company, title, position, employment_type, period, d_day)):
            continue

        employment_text = employment_type.get_text(" ", strip=True)
        if "인턴" not in employment_text and "신입" not in employment_text:
            continue

        jobs.append(
            {
                "company": company.get_text(" ", strip=True),
                "title": title.get_text(" ", strip=True),
                "link": urljoin(url, card["href"]),
                "position": position.get_text(" ", strip=True),
                "employment": employment_text,
                "period": period.get_text(" ", strip=True),
                "deadline": d_day.get_text(" ", strip=True),
            }
        )

    return jobs


if __name__ == "__main__":
    job_list = scrape_jobs()
    print(f"총 {len(job_list)}개의 채용 공고를 찾았습니다.\n")
    for job in job_list:
        print(job)
        print()
