"""공유 설정 로더 — .env에서 키 관리 (다른 MGPrj 프로젝트 관례 일치).
python-dotenv 있으면 사용, 없으면 수동 파싱 폴백. 키는 .env(gitignore)에만, 코드 하드코딩 금지."""
import os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _load():
    p = os.path.join(HERE, ".env")
    if not os.path.exists(p): return
    try:
        from dotenv import load_dotenv; load_dotenv(p)
    except ImportError:
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
_load()
FEC_API_KEY = os.environ.get("FEC_API_KEY", "DEMO_KEY")
SEC_UA = os.environ.get("SEC_USER_AGENT", "research your-email@example.com")
CONGRESS_API_KEY = os.environ.get("CONGRESS_API_KEY", "")
