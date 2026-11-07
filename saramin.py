import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from config import HEADERS, is_target_job

URL = (
    "https://www.saramin.co.kr/zf_user/jobs/public/list?"
    "cat_kewd=1750%2C1758%2C1751%2C1760%2C1761%2C1763%2C1756%2C1754%2C1755"
    "%2C2227%2C1757&job_type=4&company_cd=0%2C1%2C2%2C3%2C4%2C5%2C6%2C7"
    "%2C9%2C10&panel_type=domestic&search_optional_item=y&search_done=y"
    "&panel_count=y&preview=y"
)


def scrape_jobs(url: str = URL) -> list[dict[str, str]]:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.select("div.list_item")
    if not rows:
        raise RuntimeError("사람인 채용 공고 목록을 찾지 못했습니다.")

    jobs = []
    for row in rows:
        if not is_target_job(row.get_text(" ", strip=True)):
            continue

        company = row.select_one("div.company_nm > a.str_tit")
        title = row.select_one("div.job_tit > a")
        sectors = row.select_one("div.job_meta > span.job_sector")
        work_place = row.select_one("p.work_place")
        career = row.select_one("p.career")
        education = row.select_one("p.education")
        deadline = row.select_one("p.support_detail > span.date")

        if not all((company, title, sectors, work_place, career, education, deadline)):
            continue

        career_text = career.get_text(" ", strip=True)
        education_text = education.get_text(" ", strip=True)

        # A current university student can apply to entry-level or open-career
        # positions, but not positions requiring graduation.
        if "신입" not in career_text and "경력무관" not in career_text:
            continue
        if "대졸 이상" in education_text or "대학원" in education_text or "석사" in education_text or "대학교(4년)↑" in education_text:
            continue

        jobs.append(
            {
                "company": company.get_text(" ", strip=True),
                "title": title.get_text(" ", strip=True),
                "link": urljoin(url, title["href"]),
                "employment": f"{career_text} · {education_text}",
                "description": sectors.get_text(" ", strip=True),
                "work_place": work_place.get_text(" ", strip=True),
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
