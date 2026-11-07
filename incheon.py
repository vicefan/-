from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import HEADERS

URL = (
    "https://www.incheon.go.kr/jobs/main/recruit/search.do?"
    "page=1&srchKey=ABCD&rcrut_mndb=&frst_ocpt_cd=10034"
    "&rcrutTypCdList=050306000000&srchValNot=&srchVal="
    "&rcrutTypCdListList=050306000000&frstOcptSnList=5153"
)


def scrape_jobs(url: str = URL) -> list[dict[str, str]]:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.select(".ovw1_list > li")
    if not rows:
        raise RuntimeError("인천일자리포털 채용 공고 목록을 찾지 못했습니다.")

    jobs = []
    for row in rows:
        title = row.select_one("a.ovw1_title")
        company = row.select_one("div.ovw1_company")
        deadline = row.select_one("ul.ovw1_info span.date")
        source = row.select_one(".ovw1_logos img")
        d_day = row.select_one(".ovw1_info_header span.variant15")

        if not all((title, company, deadline, source, d_day)):
            continue

        jobs.append(
            {
                "company": company.get_text(" ", strip=True),
                "title": title.get_text(" ", strip=True),
                "link": urljoin(url, title["href"]),
                "description": row.get_text(" ", strip=True),
                "employment": row.select_one(".ovw1_info_header").get_text(
                    " ", strip=True
                ),
                "deadline": deadline.get_text(" ", strip=True),
                "d_day": d_day.get_text(" ", strip=True),
                "source": source.get("alt", "").strip(),
            }
        )

    return jobs


if __name__ == "__main__":
    job_list = scrape_jobs()
    print(f"총 {len(job_list)}개의 채용 공고를 찾았습니다.\n")
    for job in job_list:
        print(job)
        print()
