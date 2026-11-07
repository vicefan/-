import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from config import HEADERS, is_target_job

URL = (
    "https://www.jobkorea.co.kr/Theme/TemplateFreeGnoList/"
    "entry-level-internship?rlistTab=0&rOrderTab=1&rSearchText=&bpart_no=10033"
    "&spart_no=&scd=&edu_no=&pref=&jtype=3&careerTypeCode=&ctype=&jobFilter=0"
    "&listDisplayCode=2&MainPageNo=1&FreePageNo=1&psTab=100&themeNo=169"
    "&tabNo=0&giDisplayCntLimitStat=0&GIOpenTypeCode=0&pay=&pay_type_code="
    "&IsPartCodeSearch=false"
)


def scrape_jobs(url: str = URL) -> list[dict[str, str]]:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.select("div.tplList.tplJobList.listItem table tbody > tr")
    if not rows:
        raise RuntimeError("채용 공고 목록을 찾지 못했습니다.")

    jobs = []
    for row in rows:
        if not is_target_job(row.get_text(" ", strip=True)):
            continue

        company = row.select_one("td.tplCo > a")
        title = row.select_one("td.tplTit > div > strong > a")
        employment_info = row.select_one("td.tplTit > div > p.etc")
        description = row.select_one("td.tplTit > div > p.dsc")
        deadline = row.select_one("td.odd > span.date.dotum > span")

        if len(description.get_text(strip=True).split(",")) > 11:
            continue

        if not all((company, title, employment_info, description, deadline)):
            continue

        employment_text = employment_info.get_text(" ", strip=True)
        if "신입" not in employment_text or "대졸↑" in employment_text:
            continue

        jobs.append(
            {
                "company": company.get_text(" ", strip=True),
                "title": title.get_text(" ", strip=True),
                "link": urljoin(url, title["href"]),
                "employment": employment_text,
                "description": description.get_text(" ", strip=True),
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