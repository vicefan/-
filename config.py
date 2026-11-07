HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

INC_KEYWORDS = ["물류", "구매", "자재", "SCM"]

EXC_KEYWORDS = ["채용연계", "채용전환", "채용전제", "대학원", "석사", "박사", "대학원생", "대학원생 이상", "대학원 이상", "대학원졸업", "대학원졸업 이상"]


def is_target_job(text: str) -> bool:
    normalized_text = " ".join(text.split())
    return (
        any(keyword in normalized_text for keyword in INC_KEYWORDS)
        and not any(keyword in normalized_text for keyword in EXC_KEYWORDS)
    )