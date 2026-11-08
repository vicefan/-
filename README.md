# 채용 공고 페이지

`main.py`가 여러 채용 사이트의 공고를 수집해 `jobs.html`을 생성합니다.
페이지에서는 `새 공고`와 지금까지 저장된 `전체 공고`를 탭으로 전환해 볼 수 있습니다.
채용 사이트별 체크박스와 `채용 공고`/`취업 프로그램` 분류로 원하는 항목만 볼 수
있으며, `별로예요` 버튼으로 관심 없는 항목을 표시할 수 있습니다. 이 표시는 브라우저에
저장됩니다.

공고는 사이트별로 안정적인 식별 키를 만들어 중복을 제거합니다. 인하대학교 프로그램은
프로그램 ID를 기준으로 식별하므로 URL의 추적 파라미터가 바뀌어도 같은 프로그램으로
처리됩니다.

GitHub Actions의 [`update-jobs.yml`](.github/workflows/update-jobs.yml)이 매시간
`main.py`를 실행하고, 변경된 `jobs.html`과 `jobs.sqlite3`를 저장소에 반영합니다.
`index.html`은 생성된 채용 공고 페이지로 이동합니다.

## 로컬 실행

```bash
python -m pip install -r requirements.txt
python main.py
```
