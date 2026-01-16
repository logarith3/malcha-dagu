"""
Filter configuration for MALCHA-DAGU.
Based on proven filtering patterns for instrument search quality.
"""


class CrawlerConfig:
    """크롤러/API 설정"""
    
    # 가격 설정
    MIN_PRICE_KRW = 200000  # 20만원 (악기 기본)
    MIN_PRICE_PEDAL = 50000 # 5만원 (이펙터/액세서리)
    MIN_PRICE_USD = 100
    
    # 결과 개수 설정
    MAX_RESULTS_NAVER = 20
    MAX_RESULTS_USER = 20
    
    # 타임아웃
    TIMEOUT_NAVER = 5


class CategoryConfig:
    """카테고리 판별용 키워드"""

    GUITAR_BRANDS = ["fender", "gibson", "prs", "ibanez", "esp", "jackson", "gopherwood", "swing"]
    BASS_KEYWORDS = ['bass', 'precision', 'jazz bass', 'pbass', 'jbass']

    # =========================================================================
    # 모델명 별칭 매핑 (검색어 → 정식 모델명)
    # 검색 시 별칭을 정식 모델명으로 변환하여 DB 매칭 정확도 향상
    # =========================================================================
    MODEL_ALIASES = {
        # BOSS 이펙터
        'ds1': 'DS-1',
        'ds-1': 'DS-1',
        'ds2': 'DS-2',
        'sd1': 'SD-1',
        'bd2': 'BD-2',
        'mt2': 'MT-2',
        'ce5': 'CE-5',
        'dd8': 'DD-8',
        'rv6': 'RV-6',
        'tu3': 'TU-3',
        'rc5': 'RC-5',
        'katana': 'KATANA',

        # Fender 기타
        'strat': 'Stratocaster',
        'stratocaster': 'Stratocaster',
        'tele': 'Telecaster',
        'telecaster': 'Telecaster',
        'jazzmaster': 'Jazzmaster',
        'jaguar': 'Jaguar',
        'mustang': 'Mustang',

        # Gibson 기타
        'lp': 'Les Paul',
        'lespaul': 'Les Paul',
        'les paul': 'Les Paul',
        'sg': 'SG',
        'es335': 'ES-335',
        'es-335': 'ES-335',
        'flying v': 'Flying V',
        'explorer': 'Explorer',

        # 베이스
        'pbass': 'Precision Bass',
        'p-bass': 'Precision Bass',
        'precision': 'Precision Bass',
        'jbass': 'Jazz Bass',
        'j-bass': 'Jazz Bass',

        # Ibanez
        'rg': 'RG',
        'jem': 'JEM',
        'prestige': 'Prestige',
        'ts9': 'TS9',
        'ts808': 'TS808',
        'tubescreamer': 'Tube Screamer',
        'tube screamer': 'Tube Screamer',

        # PRS
        'custom24': 'Custom 24',
        'custom 24': 'Custom 24',
        'mccarty': 'McCarty',
        'se': 'SE',

        # Marshall
        'jcm800': 'JCM800',
        'jcm900': 'JCM900',
        'dsl': 'DSL',
        'plexi': 'Plexi',
    }
    # 페달 키워드 (브랜드 + 모델명 패턴 + 한글)
    PEDAL_KEYWORDS = [
        'pedal', 'stomp', 'effect', 'effects', 'effector', '이펙터', '페달',
        # 브랜드
        'boss', '보스', 'strymon', 'tc electronic', 'mxr', 'electro-harmonix', 'ehx',
        'ibanez tube screamer', 'ts808', 'ts9', 'keeley', 'walrus audio', 'jhs',
        # 이펙트 종류
        'overdrive', 'distortion', 'fuzz', 'delay', 'reverb', 'chorus', 'phaser',
        'flanger', 'compressor', 'wah', 'looper', 'tuner pedal', 'eq pedal',
        'booster', 'octave', 'tremolo', 'vibrato', 'noise gate', 'preamp pedal',
        # BOSS 모델명 패턴 (대표적인 것들)
        'ds-1', 'ds-2', 'sd-1', 'bd-2', 'od-3', 'mt-2', 'hm-2', 'md-2',
        'ce-5', 'ch-1', 'bf-3', 'ph-3', 'rv-6', 'dd-8', 'rc-5', 'tu-3',
        'ad-2', 'ad-3', 'cs-3', 'ge-7', 'ns-2', 'ps-6', 'sy-1', 'oc-5',
    ]
    AMP_KEYWORDS = ['amp', 'cabinet', 'head', 'combo', 'amplifier']
    ACOUSTIC_KEYWORDS = ['acoustic', 'martin', 'taylor', '어쿠스틱', '통기타']

    # 한글 브랜드명 매핑 (한글 검색 -> 영문 브랜드 감지용)
    BRAND_NAME_MAPPING = {
        '펜더': 'fender', '팬더': 'fender',
        '깁슨': 'gibson',
        '피알에스': 'prs',
        '아이바네즈': 'ibanez', '이바네즈': 'ibanez',
        '이에스피': 'esp',
        '잭슨': 'jackson',
        '샤벨': 'charvel',
        '쉑터': 'schecter',
        '써': 'suhr',
        '뮤직맨': 'musicman',
        '지앤엘': 'g&l', '지엔엘': 'g&l',
        '야마하': 'yamaha',
        '크래머': 'kramer',
        '그레치': 'gretsch',
        '보스': 'boss',
        '마샬': 'marshall',
        '복스': 'vox',
        '오렌지': 'orange',
        '메사': 'mesa',
        '고퍼우드': 'gopherwood',
        '스윙': 'swing',
    }
    
  

class FilterConfig:
    """필터링 설정"""

    # =========================================================================
    # [0] 블랙리스트 예외 키워드 (이 단어가 있으면 블랙리스트 무시)
    # "본품 + 액세서리 세트"는 본품이므로 통과시킴
    # =========================================================================
    BLACKLIST_EXCEPTION_KEYWORDS = [
        '세트', '동시 구매', '동시구매', '포함', '증정', '사은품',
        'set', 'bundle', 'combo', 'package', 'included', 'with',
    ]

    # =========================================================================
    # [1] 통합 블랙리스트 (이 단어가 제목에 있으면 무조건 제외)
    # =========================================================================
    BLACKLIST_KEYWORDS = [
        # 1. 상태/조건 (영문)
        'case only', 'empty', 'neck only', 'body only', 'parts only', 
        'box only', 'damaged', 'broken', 'for parts',
        
        # 2. 부품류 (영문)
        'neck', 'body', 'pickup', 'pickups', 'knob', 'knobs',
        'bridge', 'potentiometer', 'pot', 'pots',
        'part', 'parts', 'screw', 'screws', 'saddle',
        'wiring', 'truss rod', 'pickguard', 'switch', 'tuner', 'tuners',
        'cover', 'covers', 'plate', 'assembly', 'electronics', '픽업',
        
        # 2-1. 부품류 (한글)
        '넥', '넥만', '바디', '바디만', '픽업', '노브', '브릿지', '브리지',
        '부품', '나사', '너트', '키트', '조립', '배선', '픽가드', '스위치',
        '튜너', '커버', '덮개', '회로', '스피커', '알루미늄', '툴', '아노다이징', '튜닝', '본체',
        
        # 3. 액세서리류 (영문)
        'case', 'bag', 'gig bag', 'hardcase', 'strap', 'cable',
        'capo', 'hanger', 'sticker', 'picks', 'slide',
        'string', 'polish', 'cloth', 'mini', '미니', 'adapter', '모자', '자전거',  # '손잡이' 제거 (왼손잡이 기타 오탐 방지)
        
        # 3-1. 액세서리류 (한글)
        '케이스', '가방', '하드케이스', '긱백', '스트랩', '케이블',
        '카포', '스탠드', '거치대', '슬라이드', '줄', '어댑터',
        
        # 4. 문서/잡동사니
        'manual', 'instruction', 'warranty', 'certificate', 'book',
        'logo', 'decal', 'poster', 'catalog',
        '설명서', '메뉴얼', '보증서', '교본', '로고', '포스터',
        
        # 5. 짝퉁/복제품
        'copy', 'replica', 'clone', 'fake', 'style', 'type',
        '복사', '복제', '모조', '짝퉁', '카피', '레플리카', '미니어처',
        
        # 6. 불량/파손
        '파손', '고장', '불량', '흠집', '부러짐', '깨짐', 'junk'
    ]
    
    # =========================================================================
    # [2] 브랜드 하이어라키 (상위 브랜드 검색 시 하위 브랜드 제외)
    # =========================================================================
    BRAND_HIERARCHY = {
        'fender': [
            'squier', 'squire', 'affinity', 'bullet', 'sonic',
            'classic vibe', 'cv', 'paranormal', 'contemporary',
            'fender clone', 'copy', 'replica', 'mini', 'loog', '스콰이어', '스퀴어',
        ],
        'gibson': [
            'epiphone', 'maestro', 'baldwin', 'kramer',
            'gibson style', 'gibson copy', 'replica', 'chibson', '에피폰',
        ],
        'prs': ['se', 's2', 'student edition'],
        'esp': ['ltd', 'edwards', 'grassroots'],
        'musicman': ['sterling', 'sub', 's.u.b'],
        'g&l': ['tribute'],
        'lakland': ['skyline'],
    }
    
    # =========================================================================
    # [3] 토큰 동의어 (모델명 매칭 확장)
    # =========================================================================
    TOKEN_SYNONYMS = {
        'stratocaster': ['strat', 'st'],
        'telecaster': ['tele', 'tl'],
        'les paul': ['lp', 'lespaul'],
        'precision': ['pbass', 'p-bass', 'p bass'],
        'jazz bass': ['jbass', 'j-bass', 'j bass'],
        'mexico': ['mexico', 'mexican', 'mim', 'player'],
        'japan': ['japan', 'japanese', 'mij', 'cij'],
        'usa': ['usa', 'american', 'mia'],
        'custom': ['custom', 'cs', 'masterbuilt'],
    }
    
    # =========================================================================
    # [4] 카테고리 불일치 필터 키워드
    # =========================================================================
    
    # 기타/베이스 검색 시 페달 제외용
    CATEGORY_PEDAL_KEYWORDS = [
        'pedal', 'stomp', 'stompbox', 'effect', 'effects', 'fx',
        'overdrive', 'distortion', 'fuzz', 'boost', 'booster',
        'delay', 'reverb', 'echo', 'chorus', 'flanger', 'phaser',
        'tremolo', 'vibrato', 'compressor', 'limiter',
        'wah', 'wah-wah', 'octave', 'harmonizer',
        'eq', 'equalizer', 'looper', 'multi-effect', 'pedalboard',
        '페달', '이펙터', '이펙트', '스톰프',
        '오버드라이브', '디스토션', '퍼즈', '부스터',
        '딜레이', '리버브', '코러스', '컴프레서', '와우', '루퍼',
    ]
    
    # 기타/베이스 검색 시 앰프 제외용
    CATEGORY_AMP_KEYWORDS = [
        'amplifier', 'amp', 'amp head', 'combo', 'combo amp',
        'cabinet', 'cab', 'head', 'stack', 'half stack', 'full stack',
        'rumble', 'bassman', 'twin reverb', 'deluxe reverb',  # 'deluxe' 단독 제거 (Les Paul Deluxe 오탐 방지)
        'princeton', 'champ', 'super', 'vibrolux',
        'marshall', 'vox', 'orange', 'mesa', 'boogie', 'peavey', 'ampeg',
        'roland', 'boss katana', 'blackstar',
        '앰프', '콤보', '콤보앰프', '캐비넷', '헤드앰프', '스택',
    ]
    
    # 페달 검색 시 기타/베이스 본체 제외용
    CATEGORY_INSTRUMENT_KEYWORDS = [
        'electric guitar', 'acoustic guitar', 'bass guitar',
        '일렉기타', '일렉트릭 기타', '어쿠스틱', '베이스기타',
    ]
    
    # BASS/GUITAR 검색 시 어쿠스틱 제외용
    CATEGORY_ACOUSTIC_KEYWORDS = [
        'acoustic bass', 'acoustic-electric bass', 'semi-acoustic bass',
        'hollow body bass', 'semi-hollow bass',
        'acoustic guitar', 'acoustic-electric', 'semi-acoustic',
        'hollow body', 'semi-hollow',
        '어쿠스틱베이스', '어쿠스틱 베이스', '통베이스',
        '어쿠스틱기타', '어쿠스틱 기타', '통기타',
    ]
    
    # =========================================================================
    # [5] 쿼리 제외 키워드 (API 요청 시 쿼리에 -키워드 추가)
    # =========================================================================
    QUERY_EXCLUSION_KEYWORDS = [
        # 전원/케이블류
        '어댑터', '아답터', '케이블', '파워', '전원',
        # 부품류
        '노브', '잭', '브릿지', '픽업', '새들',
        # 악세서리류
        '스트랩', '케이스', '가방', '거치대',
        # 기타
        '스티커', '배터리', '충전기',
    ]
    
    # =========================================================================
    # [6] 액세서리 카테고리 (category3, category4에서 제외할 카테고리)
    # =========================================================================
    ACCESSORY_CATEGORY_BLACKLIST = [
        # category4 값으로 자주 오는 액세서리 분류
        '악기부품', '기타부품', '베이스부품', '부품',
        '악기케이블', '케이블', '음향케이블',
        '기타액세서리', '베이스액세서리', '악세사리', '액세서리',
        '기타케이스', '베이스케이스', '하드케이스', '긱백',
        '기타스탠드', '악기스탠드', '거치대',
        '기타스트랩', '스트랩',
        '기타줄', '베이스줄', '현', '스트링',
        '기타픽', '피크', '픽',
        '기타카포', '카포',
        '어댑터', '전원장치', '파워서플라이',
    ]
    
    # =========================================================================
    # [7] 유효한 악기 카테고리 (이 카테고리면 '본품'으로 간주)
    # =========================================================================
    VALID_INSTRUMENT_CATEGORIES = {
        # 기타류
        'guitar': ['일렉기타', '일렉트릭기타', '어쿠스틱기타', '클래식기타', '기타'],
        'bass': ['베이스기타', '일렉트릭베이스', '어쿠스틱베이스', '베이스'],
        'pedal': ['이펙터', '기타이펙터', '베이스이펙터', '멀티이펙터', '페달'],
        'amp': ['기타앰프', '베이스앰프', '앰프', '콤보앰프', '앰프헤드'],
    }
    
    # =========================================================================
    # [8] productType 필터 (상품 타입별 신뢰도)
    # =========================================================================
    # 1: 일반상품(가격비교O), 2: 일반상품(가격비교X), 3: 일반상품(가격비교 매칭)
    # 4: 중고상품, 5: 단종상품, 6: 판매예정상품
    VALID_PRODUCT_TYPES = [1, 2, 3]  # 중고(4), 단종(5), 판매예정(6) 제외
