import requests
import os
import re
from urllib.parse import quote
import logging

# =========================================================
# [1] 설정 및 초기화
# =========================================================
logger = logging.getLogger(__name__)

# High-Quality Edition 유틸리티 임포트
try:
    from .crawler_utils import (
        get_random_headers,
        apply_jitter,
        filter_price_outliers_iqr,
        calculate_match_score,
        extract_entities,
        normalize_synonym_tokens,
        validate_image_url
    )

    logger.info("✅ High-Quality Edition 유틸리티를 성공적으로 불러왔습니다.")
except ImportError as e:
    logger.warning(f"⚠️ High-Quality Edition 유틸리티 임포트 실패: {e}")


    # 폴백 함수 정의
    def get_random_headers():
        return {"User-Agent": "Mozilla/5.0"}


    def apply_jitter(*args, **kwargs):
        pass


    def filter_price_outliers_iqr(results, *args, **kwargs):
        return results


    def calculate_match_score(*args, **kwargs):
        return 50


    def extract_entities(query):
        return {}


    def normalize_synonym_tokens(text):
        return text


    def validate_image_url(url):
        return True

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
}

# 🎸 리버브(Reverb) 카테고리 UUID 매핑
REVERB_CAT_MAP = {
    "GUITAR": "dfd39027-d134-4353-b9e4-57dc6be791b9",
    "BASS": "53a9c7d7-d73d-4e7f-905c-553503e50a90",
    "ACOUSTIC": "3ca3eb03-7eac-477d-b253-15ce603d2550",
    "PEDAL": "fa10f97c-dd98-4a8f-933b-8cb55eb653dd",
    "AMP": "09055aa7-ed49-459d-9452-aa959f288dc2"
}

# 설정 가져오기 시도
try:
    from .config import CategoryConfig, FilterConfig, CrawlerConfig

    logger.info("✅ config.py 파일을 성공적으로 불러왔습니다.")
except ImportError:
    logger.warning("⚠️ config.py를 찾을 수 없습니다. 기본 설정 사용.")


    class CategoryConfig:
        GUITAR_BRANDS = ["fender", "gibson", "prs", "ibanez"]
        BASS_KEYWORDS = ['bass']
        PEDAL_KEYWORDS = ['pedal', 'stomp', 'effect']
        AMP_KEYWORDS = ['amp', 'cabinet']
        ACOUSTIC_KEYWORDS = ['acoustic']


    class FilterConfig:
        BLACKLIST_KEYWORDS = []  # config.py를 사용하지 않으면 블랙리스트 없음
        TOKEN_SYNONYMS = {}
        BRAND_PAIRS = {}
        BRAND_HIERARCHY = {}
        LOWER_BRANDS = []
        # 카테고리 필터 폴백 (기본값)
        CATEGORY_PEDAL_KEYWORDS = ['pedal', 'effect', 'stomp']
        CATEGORY_AMP_KEYWORDS = ['amp', 'amplifier', 'combo']
        CATEGORY_INSTRUMENT_KEYWORDS = ['electric guitar', 'bass guitar']
        CATEGORY_ACOUSTIC_KEYWORDS = ['acoustic', 'akustik']


    class CrawlerConfig:
        MIN_PRICE_USD = 100
        MIN_PRICE_KRW = 100000
        MAX_RESULTS_REVERB = 10
        TIMEOUT_REVERB = 10


def get_blacklist():
    """
    블랙리스트 로드 (config.py만 사용, 쉼표 누락 방어 로직 포함)
    - config.py의 BLACKLIST_KEYWORDS만 사용 (FALLBACK 사용 안 함)
    - 비정상적으로 긴 단어는 경고 출력 (쉼표 누락으로 문자열 결합된 경우)
    - 중복 제거 및 정규화
    - 대소문자 자동 변환 (config에 대문자로 써도 됨)
    """
    raw_list = getattr(FilterConfig, 'BLACKLIST_KEYWORDS', [])

    if not raw_list:
        logger.error("❌ config.py에 BLACKLIST_KEYWORDS가 없습니다!")
        return []

    result = []
    for item in raw_list:
        if item:
            word = str(item).strip().lower()
            # 비정상적으로 긴 단어 감지 (쉼표 누락으로 문자열 결합된 경우)
            if len(word) > 25:
                logger.warning(f"⚠️ 블랙리스트에 비정상적으로 긴 단어 발견: '{word}' (쉼표 누락 가능성 있음)")
            result.append(word)

    # 중복 제거
    result = list(set(result))
    logger.info(f"✅ 블랙리스트 로드 완료: {len(result)}개 키워드")
    return result


def get_category_keywords(config_attr_name, default_fallback=[]):
    """
    카테고리 필터 키워드 로드 (대소문자 자동 변환)
    - config.py의 키워드를 소문자로 변환
    - config에 'Laurel', 'FA-450CE' 같이 대문자로 써도 자동으로 소문자 변환
    """
    raw_list = getattr(FilterConfig, config_attr_name, default_fallback)

    if not raw_list:
        return []

    # 모든 키워드를 소문자로 변환
    result = [str(item).strip().lower() for item in raw_list if item]
    return result


GLOBAL_BLACKLIST = get_blacklist()


# =========================================================
# [2] 공통 유틸리티
# =========================================================

def get_exchange_rate():
    """
    환율 API 호출 (USD -> KRW)
    - 실패 시 기본값 1400 반환
    """
    api_key = os.getenv('EXCHANGE_RATE_API_KEY')
    if not api_key:
        logger.warning("⚠️ EXCHANGE_RATE_API_KEY가 없어 기본 환율(1400) 사용")
        return 1400

    try:
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD"
        resp = requests.get(url, timeout=3)

        if resp.status_code == 200:
            rate = resp.json()['conversion_rates']['KRW']
            logger.info(f"✅ 환율 API 호출 성공: 1 USD = {rate} KRW")
            return rate
        else:
            logger.warning(f"⚠️ 환율 API 오류 ({resp.status_code}), 기본 환율(1400) 사용")
            return 1400

    except requests.exceptions.Timeout:
        logger.warning("⚠️ 환율 API 타임아웃, 기본 환율(1400) 사용")
        return 1400
    except requests.exceptions.RequestException as e:
        logger.warning(f"⚠️ 환율 API 네트워크 오류: {e}, 기본 환율(1400) 사용")
        return 1400
    except (KeyError, ValueError) as e:
        logger.warning(f"⚠️ 환율 API 응답 파싱 실패: {e}, 기본 환율(1400) 사용")
        return 1400
    except Exception as e:
        logger.error(f"❌ 환율 API 예상치 못한 오류: {e}, 기본 환율(1400) 사용")
        return 1400


def get_final_category(instrument):
    text = f"{instrument.brand} {instrument.model_name}".lower()
    if any(kw in text for kw in CategoryConfig.BASS_KEYWORDS): return "BASS"
    if any(kw in text for kw in CategoryConfig.PEDAL_KEYWORDS): return "PEDAL"
    if any(kw in text for kw in CategoryConfig.AMP_KEYWORDS): return "AMP"
    if any(kw in text for kw in CategoryConfig.ACOUSTIC_KEYWORDS): return "ACOUSTIC"
    model_cat = str(instrument.category).upper() if instrument.category else "PENDING"
    if model_cat in REVERB_CAT_MAP: return model_cat
    return "GUITAR"


def validate_tokens(target_name, title):
    """
    모델명 토큰 검증 (동의어 지원)
    - 모델명(target_name)의 주요 토큰이 제목(title)에 포함되어 있는지 확인
    - 토큰 중 하나라도 매칭되면 통과 (OR 조건)
    - 동의어도 확인 (TOKEN_SYNONYMS)
    """
    clean_target = target_name.replace("[Pending] Pending...", "").strip()
    tokens = [t.lower() for t in clean_target.split() if len(t) > 1]

    # 토큰이 없으면 통과
    if not tokens:
        return True

    title_lower = title.lower()

    # 모든 토큰 중 하나라도 매칭되면 통과
    for token in tokens:
        # 직접 매칭
        if token in title_lower:
            return True
        # 동의어 매칭
        synonyms = FilterConfig.TOKEN_SYNONYMS.get(token, [])
        if any(syn in title_lower for syn in synonyms):
            return True

    # 어떤 토큰도 매칭 안 되면 탈락
    return False


def check_brand_integrity_v6(target_brand, title, category):
    target_lower = target_brand.lower().strip()
    if "pending" in target_lower: return True
    core_brand = target_lower.split()[0] if target_lower else ""
    if not core_brand or len(core_brand) <= 1: return True
    if hasattr(FilterConfig, 'BRAND_HIERARCHY') and core_brand in FilterConfig.BRAND_HIERARCHY:
        for lower_brand in FilterConfig.BRAND_HIERARCHY[core_brand]:
            if lower_brand in title.lower(): return False
    if core_brand in title.lower(): return True
    return False


def is_category_mismatch(search_category, title):
    """
    카테고리 불일치 검사 (config.py에서 키워드 로드, 대소문자 자동 변환)
    - 기타/베이스 검색 시 페달/앰프가 섞이면 제외
    - BASS/GUITAR 검색 시 어쿠스틱 제외 (일렉 위주)
    - 페달 검색 시 기타 본체가 섞이면 제외
    - config.py에 대문자로 입력해도 자동으로 소문자 변환됨
    """
    title_lower = title.lower()

    # GUITAR/BASS 검색 시 페달/앰프/어쿠스틱 제외
    if search_category in ['GUITAR', 'BASS']:
        pedal_keywords = get_category_keywords('CATEGORY_PEDAL_KEYWORDS', ['pedal', 'effect'])
        amp_keywords = get_category_keywords('CATEGORY_AMP_KEYWORDS', ['amp', 'amplifier'])
        acoustic_keywords = get_category_keywords('CATEGORY_ACOUSTIC_KEYWORDS', ['acoustic'])

        if any(kw in title_lower for kw in pedal_keywords):
            return True
        if any(kw in title_lower for kw in amp_keywords):
            return True
        # 일렉 위주 검색: 어쿠스틱 제외
        if any(kw in title_lower for kw in acoustic_keywords):
            return True

    # ACOUSTIC 검색 시 페달/앰프만 제외 (어쿠스틱은 허용)
    if search_category == 'ACOUSTIC':
        pedal_keywords = get_category_keywords('CATEGORY_PEDAL_KEYWORDS', ['pedal', 'effect'])
        amp_keywords = get_category_keywords('CATEGORY_AMP_KEYWORDS', ['amp', 'amplifier'])

        if any(kw in title_lower for kw in pedal_keywords):
            return True
        if any(kw in title_lower for kw in amp_keywords):
            return True

    # PEDAL 검색 시 기타/베이스 본체 제외
    if search_category == 'PEDAL':
        instrument_keywords = get_category_keywords('CATEGORY_INSTRUMENT_KEYWORDS', ['electric guitar', 'bass guitar'])
        if any(kw in title_lower for kw in instrument_keywords):
            return True

    # AMP 검색 시 페달 제외
    if search_category == 'AMP':
        pedal_keywords = get_category_keywords('CATEGORY_PEDAL_KEYWORDS', ['pedal', 'effect'])
        if any(kw in title_lower for kw in pedal_keywords):
            return True

    return False


# =========================================================
# [3] 리버브 (Reverb)
# =========================================================

def fetch_reverb_data(instrument, category=None):
    token = os.getenv('REVERB_TOKEN')
    if not token:
        logger.error("🚫 [Reverb] REVERB_TOKEN 없음")
        return []

    rate = get_exchange_rate()
    brand = instrument.brand.strip()
    model = instrument.model_name.strip()
    if category is None: category = get_final_category(instrument)
    target_uuid = REVERB_CAT_MAP.get(category, REVERB_CAT_MAP["GUITAR"])
    min_price_usd = CrawlerConfig.MIN_PRICE_USD.get(category, 100) if isinstance(CrawlerConfig.MIN_PRICE_USD,
                                                                                 dict) else CrawlerConfig.MIN_PRICE_USD

    search_query = f"{brand} {model}"
    entities = extract_entities(search_query)
    accumulated_results = []
    target_count = getattr(CrawlerConfig, 'MAX_RESULTS_REVERB', 10)

    logger.info(f"🔍 [Reverb] 검색 시작: '{search_query}' (목표: {target_count}개)")

    # 최대 5페이지까지 탐색 (충분한 매물 확보를 위해)
    for page in range(1, 6):
        # 목표 개수 달성 시 중단
        if len(accumulated_results) >= target_count:
            logger.info(f"✅ [Reverb] 목표 개수({target_count}개) 달성, 페이지 탐색 중단")
            break

        apply_jitter()
        headers = {"Authorization": f"Bearer {token}", "Accept-Version": "3.0", **get_random_headers()}
        search_url = (
            f"https://api.reverb.com/api/listings?query={quote(search_query)}&make={quote(brand)}&"
            f"category_uuid={target_uuid}&price_min={min_price_usd}&sort=price|asc&per_page=40&page={page}"
        )

        try:
            resp = requests.get(search_url, headers=headers, timeout=CrawlerConfig.TIMEOUT_REVERB)
            resp.raise_for_status()
            listings = resp.json().get('listings', [])

            if not listings:
                logger.info(f"ℹ️ [Reverb] P{page}: 더 이상 검색 결과가 없습니다.")
                break

            # 필터링 카운터
            p_total = len(listings)
            p_brand, p_token, p_blacklist, p_category = 0, 0, 0, 0

            for item in listings:
                title = item.get('title', '')

                # [필터 1] 브랜드 무결성 검사
                if not check_brand_integrity_v6(brand, title, category):
                    p_brand += 1
                    continue

                # [필터 2] 모델 토큰 검사
                if not validate_tokens(model, title):
                    p_token += 1
                    continue

                # [필터 3] 블랙리스트 검사
                title_lower = title.lower()
                if any(blackword in title_lower for blackword in GLOBAL_BLACKLIST):
                    p_blacklist += 1
                    continue

                # [필터 4] 카테고리 불일치 검사
                if is_category_mismatch(category, title):
                    p_category += 1
                    continue

                # 통과 - 결과에 추가
                image_url = item.get('photos', [{}])[0].get('_links', {}).get('large', {}).get('href', None)
                accumulated_results.append({
                    'id': item.get('id', ''),
                    'title': title,
                    'shop_name': 'Reverb',
                    'price': int(float(item['price']['amount']) * rate),
                    'currency': 'KRW',
                    'is_used': item.get('condition', {}).get('uuid') != 'new',
                    'deal_url': item['_links']['web']['href'],
                    'location': 'Global',
                    'image': image_url,
                    'score': calculate_match_score(search_query, title, image_url, entities),
                    'site_badge': 'Reverb'
                })

            # 페이지별 필터링 결과 로그
            approved = p_total - p_brand - p_token - p_blacklist - p_category
            logger.info(
                f"📊 [Reverb] P{page} 결과: 수집({p_total}) | 브랜드탈락({p_brand}) | "
                f"토큰탈락({p_token}) | 블랙리스트탈락({p_blacklist}) | 카테고리탈락({p_category}) | 최종승인({approved})"
            )

        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ [Reverb] HTTP 오류 (P{page}): {e}")
            break
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [Reverb] 네트워크 오류 (P{page}): {e}")
            break
        except Exception as e:
            logger.error(f"❌ [Reverb] 예상치 못한 오류 (P{page}): {e}")
            break

    logger.info(f"🏁 [Reverb] 최종 반환 개수: {len(accumulated_results[:target_count])}개")
    return accumulated_results[:target_count]


# =========================================================
# [5] 네이버 쇼핑 (Naver Shopping) - API 연동 (최종 로그 강화 버전)
# =========================================================

def fetch_naver_data(instrument, category=None):
    client_id = os.getenv('NAVER_CLIENT_ID')
    client_secret = os.getenv('NAVER_CLIENT_SECRET')

    # [로그 추가] 환경 변수 로드 상태 확인
    if not client_id or not client_secret:
        logger.error(
            f"🚫 [Naver] 인증 정보 누락 - ID: {'성공' if client_id else '실패'}, Secret: {'성공' if client_secret else '실패'}")
        return []

    try:
        brand = getattr(instrument, 'brand', '').strip()
        model = getattr(instrument, 'model_name', '').strip()
    except AttributeError:
        brand = instrument.get('brand', '').strip()
        model = instrument.get('model_name', '').strip()

    search_keyword = f"{brand} {model}".replace("[Pending] Pending...", "").strip()
    if not search_keyword:
        logger.warning("⚠️ [Naver] 검색어가 없어 호출을 중단합니다.")
        return []

    if category is None:
        category = get_final_category(instrument)

    min_price_krw = getattr(CrawlerConfig, 'MIN_PRICE_KRW', 100000)
    accumulated_results = []
    start_index = 1

    logger.info(f"🔍 [Naver] 서비스 호출 시작: '{search_keyword}' (최소가격: {min_price_krw})")

    for i in range(3):  # max_fetches = 3
        try:
            url = "https://openapi.naver.com/v1/search/shop.json"
            headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
            params = {"query": search_keyword, "display": 100, "start": start_index, "sort": "sim",
                      "exclude": "rental:cbshop"}

            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code != 200:
                logger.error(f"❌ [Naver] API 오류 ({resp.status_code}): {resp.text}")
                break

            items = resp.json().get('items', [])
            if not items:
                logger.info(f"ℹ️ [Naver] P{i + 1}: 검색 결과가 더 이상 없습니다.")
                break

            # --- 필터링 단계별 카운팅을 위한 변수 ---
            p_total = len(items)
            p_price, p_brand, p_token, p_blacklist, p_category = 0, 0, 0, 0, 0

            for item in items:
                # HTML 태그 제거 및 공백 정리
                clean_title = re.sub(r'<[^>]+>', '', item['title']).replace('\xa0', ' ').strip()
                try:
                    lprice = int(item['lprice'])
                except:
                    continue

                # ============================================
                # [필터 1] 최소 가격 검사
                # - 너무 싼 물건(부품, 케이스 등) 제외
                # - 예: 100,000원 미만은 완제품이 아닐 가능성 높음
                # ============================================
                if lprice < min_price_krw:
                    p_price += 1
                    continue

                # ============================================
                # [필터 2] 브랜드 무결성 검사
                # - 검색한 브랜드(Fender)와 다른 브랜드(Squier) 제외
                # - 브랜드 계층 구조(상위/하위) 확인
                # - 예: "Fender" 검색 시 "Squier by Fender"는 탈락
                # ============================================
                if not check_brand_integrity_v6(brand, clean_title, category):
                    p_brand += 1
                    continue

                # ============================================
                # [필터 3] 모델 토큰 검사
                # - 검색한 모델명(Telecaster)이 타이틀에 있는지 확인
                # - 동의어 포함 (Tele, Strat 등)
                # - 예: "Telecaster" 검색 시 "Stratocaster"는 탈락
                # ============================================
                if not validate_tokens(model, clean_title):
                    p_token += 1
                    continue

                # ============================================
                # [필터 4] 블랙리스트 검사 (대소문자 구분 없음)
                # - 'case only', 'neck only', 'body only' 등 부품/케이스 제외
                # - GLOBAL_BLACKLIST는 이미 소문자로 변환되어 있음
                # - title_lower도 소문자 변환 -> 대소문자 무관하게 비교
                # - 예: "Fender Telecaster CASE" -> 'case' 포함으로 탈락
                # ============================================
                title_lower = clean_title.lower()
                if any(blackword in title_lower for blackword in GLOBAL_BLACKLIST):
                    p_blacklist += 1
                    continue

                # ============================================
                # [필터 5] 카테고리 불일치 검사
                # - 기타 검색 시 페달/앰프 제외
                # - 페달 검색 시 기타 본체 제외
                # - 예: 기타 검색 중 "이펙트 페달" 제목 → 탈락
                # ============================================
                if is_category_mismatch(category, clean_title):
                    p_category += 1
                    continue

                # ============================================
                # ✅ 모든 필터 통과 - 최종 승인!
                # 이 매물은:
                # 1) 최소 가격 이상
                # 2) 검색한 브랜드가 맞음
                # 3) 검색한 모델명이 포함됨
                # 4) 부품/케이스가 아닌 완제품
                # 5) 검색 카테고리와 일치
                # ============================================
                accumulated_results.append({
                    'id': item.get('productId', ''),
                    'title': clean_title,
                    'shop_name': item.get('mallName', 'Naver'),
                    'price': lprice,
                    'currency': 'KRW',
                    'is_used': '중고' in clean_title or item.get('productType') in ['2', '4', '5', '6'],
                    'deal_url': item.get('link'),
                    'location': 'Korea',
                    'image': item.get('image', ''),
                    'score': calculate_match_score(search_keyword, clean_title, item.get('image', ''), {}),
                    'site_badge': 'Naver'
                })

            # [로그 추가] 필터링 결과 요약 출력
            logger.info(
                f"📊 [Naver] P{i + 1} 결과: 수집({p_total}) | 가격탈락({p_price}) | 브랜드탈락({p_brand}) | "
                f"토큰탈락({p_token}) | 블랙리스트탈락({p_blacklist}) | 카테고리탈락({p_category}) | "
                f"최종승인({p_total - p_price - p_brand - p_token - p_blacklist - p_category})")

            start_index += 100
        except Exception as e:
            logger.error(f"⚠️ [Naver] 호출 중 예외: {e}")
            break

    # 점수와 가격 순으로 정렬
    accumulated_results.sort(key=lambda x: (-x['score'], x['price']))

    # 설정된 최대 개수만큼 반환
    max_results = getattr(CrawlerConfig, 'MAX_RESULTS_NAVER', 10)
    logger.info(f"🏁 [Naver] 최종 반환 개수: {len(accumulated_results[:max_results])}개")
    return accumulated_results[:max_results]