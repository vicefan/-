# 채용 공고 페이지

`main.py`가 여러 채용 사이트의 공고를 수집해 `jobs.html`을 생성합니다.

GitHub Actions의 [`update-jobs.yml`](.github/workflows/update-jobs.yml)이 매시간
`main.py`를 실행하고, 변경된 `jobs.html`과 `jobs.sqlite3`를 저장소에 반영합니다.
`index.html`은 생성된 채용 공고 페이지로 이동합니다.

## 로컬 실행

```bash
python -m pip install -r requirements.txt
python main.py
```
