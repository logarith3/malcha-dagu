import os


class CrawlerConfig:
    # 기본 설정
    TIMEOUT_REVERB = 10
    TIMEOUT_DIGIMART = 15
    MAX_RESULTS_REVERB = 10
    MAX_RESULTS_DIGIMART = 10
    MAX_RESULTS_NAVER = 10  # 네이버 최대 반환 개수

    # 가격 설정 (USD, JPY, KRW)
    MIN_PRICE_USD = 100
    MIN_PRICE_JPY = 10000
    MIN_PRICE_KRW = 100000


class CategoryConfig:
    # 카테고리 매핑용 키워드
    GUITAR_BRANDS = ["fender", "gibson", "prs", "ibanez"]
    BASS_KEYWORDS = ['bass', 'precision', 'jazz bass']
    PEDAL_KEYWORDS = ['pedal', 'stomp', 'effect', 'boss', 'strymon']
    AMP_KEYWORDS = ['amp', 'cabinet', 'head', 'combo']
    ACOUSTIC_KEYWORDS = ['acoustic', 'martin', 'taylor']


class FilterConfig:
    """필터링 설정 (통합됨)"""

    # [1] 통합 블랙리스트 (이 단어가 제목에 있으면 무조건 제외)
    BLACKLIST_KEYWORDS = [
        # 1. 상태/조건 (영문)
        'case only', 'empty', 'neck only', 'body only', 'parts only', 'box', 'damaged', 'broken',

        # 2. 부품류 (영문 + 한글)
        'neck', 'body', 'pickup', 'pickups', 'pick up', 'pick ups', 'knob', 'knobs',
        'bridge', 'potentiometer', 'pot', 'pots',
        'part', 'parts', 'screw', 'screws', 'nut', 'saddle', 'kit', 'blem', 'tip', 'jack',
        'boutons', 'tonehounds', 'wiring', 'truss rod', 'pickguard',
        'switch', 'tuner', 'tuners', 'machine head', 'peg', 'pegs', 'bezel', 'plate', 'assembly',
        'cover', 'covers', 'control cover', 'pickup cover', 'bridge cover', 'ashtray cover',
        'control plate', 'backplate', 'back plate', 'tremolo cover', 'cavity cover',
        'uke', 'ukulele', 'case',
        'electronics', 'electronic', 'electronics set', 'electronic set', 'electronics kit', 'wiring kit',
        '넥', '넥만', '바디', '바디만', '픽업', '노브', '브릿지', '브리지', '포텐', '포텐셔미터',
        '부품', '나사', '너트', '새들', '키트', '조립', '조립품', '잭',
        '배선', '배선키트', '트러스로드', '픽가드', '스위치', '튜너', '페그',
        '커버', '덮개', '픽업커버', '컨트롤커버', '브릿지커버', '트레몰로커버',
        '전자회로', '회로', '일렉트로닉스', '우쿨렐레'

        # 3. 액세서리류 (영문 + 한글)
        'case', 'bag', 'gig bag', 'hardcase', 'strap', 'cable',
        'capo', 'stand', 'hanger', 'sticker', 'picks', 'slide', 'metronome',
        'string', 'polish', 'cloth', 'wipes',
        '케이스', '가방', '하드케이스', '긱백', '스트랩', '케이블', '줄',
        '카포', '스탠드', '거치대', '스티커', '픽', '슬라이드', '메트로놈',
        '현', '광택제', '클로스', '물티슈',

        # 4. 문서/잡동사니 (영문 + 한글)
        'manual', 'instruction', 'warranty', 'certificate', 'book', 'magazine',
        'logo', 'decal', 'poster', 'catalog', 'brochure',
        '설명서', '메뉴얼', '보증서', '인증서', '교본', '교재', '잡지',
        '로고', '스티커', '포스터', '카탈로그', '브로슈어',

        # 5. 기타 (한글 특화)
        '복사', '복제', '모조', '짝퉁', '카피', '레플리카', '미니어처',
        '파손', '고장', '불량', '흠집', '부러짐', '깨짐'
    ]

    # [2] 브랜드 하이어라키 (상위 브랜드 검색 시 하위 브랜드 제외)
    # 예: 'Fender' 검색 시 -> 'Squier', 'Affinity' 들어간 매물 삭제
    BRAND_HIERARCHY = {
        'fender': [
            'squier', 'squire',  # 오타 포함
            'affinity', 'bullet', 'sonic',  # 저가 라인
            'classic vibe', 'cv',  # 인기 라인
            'paranormal', 'contemporary',
            'fender clone', 'copy', 'replica', 'style', 'type',  # 짝퉁 방지
            'mini','loog','replacement'
        ],
        'gibson': [
            'epiphone', 'maestro', 'baldwin', 'kramer',
            'gibson style', 'gibson copy', 'replica', 'chibson'
        ],
        'prs': ['se', 's2', 'student edition'],
        'esp': ['ltd', 'edwards', 'grassroots'],
        'musicman': ['sterling', 'sub', 's.u.b'],
        'g&l': ['tribute'],
        'lakland': ['skyline'],
        'suhr': ['rasmus']
    }

    # [3] 브랜드 동의어 (검색어 확장용이 아님, 브랜드 정합성 체크용)
    TOKEN_SYNONYMS = {
        'mexico': ['mexico', 'mexican', 'mim', 'player'],
        'japan': ['japan', 'japanese', 'mij', 'cij'],
        'usa': ['usa', 'american', 'mia'],
        'custom': ['custom', 'cs', 'masterbuilt'],
    }

    # [4] 브랜드 페어 (하위 브랜드 검색 시 상위 브랜드 이름 허용)
    # 주의: 반대 경우는 허용하지 않음 (Fender -> Squier X)
    BRAND_PAIRS = {
        'squier': 'fender',  # Squier by Fender 허용
        'epiphone': 'gibson',  # Epiphone by Gibson 허용
        'ltd': 'esp',
        'se': 'prs',
        'sterling': 'musicman',
        'tribute': 'g&l'
    }

    # 하위 브랜드 목록 (검색 로직 보조)
    LOWER_BRANDS = ['squier', 'epiphone', 'ltd', 'se', 'sterling', 'tribute']

    # [5] 카테고리 불일치 필터 키워드 (기타/베이스/페달/앰프 구분용)

    # 기타/베이스 검색 시 페달 제외용
    CATEGORY_PEDAL_KEYWORDS = [
        # 영문 - 기본
        'pedal', 'stomp', 'stompbox', 'effect', 'effects', 'fx',
        # 영문 - 페달 타입
        'overdrive', 'distortion', 'fuzz', 'boost', 'booster',
        'delay', 'reverb', 'echo', 'chorus', 'flanger', 'phaser',
        'tremolo', 'vibrato', 'compressor', 'limiter',
        'wah', 'wah-wah', 'octave', 'harmonizer', 'pitch shifter',
        'eq', 'equalizer', 'filter', 'envelope', 'synth',
        'looper', 'sampler', 'multi-effect', 'pedalboard',
        # 한글
        '페달', '이펙터', '이펙트', '스톰프',
        '오버드라이브', '디스토션', '퍼즈', '부스터',
        '딜레이', '리버브', '에코', '코러스', '플랜저', '페이저',
        '트레몰로', '비브라토', '컴프레서', '리미터',
        '와우', '옥타브', '하모나이저', '이퀄라이저', '루퍼'
    ]

    # 기타/베이스 검색 시 앰프 제외용
    CATEGORY_AMP_KEYWORDS = [
        # 앰프 타입
        'amplifier', 'amp', 'amp head', 'combo', 'combo amp', 'cabinet', 'cab',
        'head', 'stack', 'half stack', 'full stack',
        # Fender 앰프 시리즈
        'rumble', 'bassman', 'twin', 'twin reverb', 'deluxe', 'deluxe reverb',
        'princeton', 'champ', 'super', 'vibrolux', 'pro',
        # 기타 유명 앰프 브랜드
        'marshall', 'vox', 'orange', 'mesa', 'boogie', 'peavey', 'ampeg',
        'roland', 'boss katana', 'blackstar', 'hughes', 'kettner',
        # 한글
        '앰프', '콤보', '콤보앰프', '캐비넷', '헤드앰프', '스택', '럼블'
    ]

    # 페달 검색 시 기타/베이스 본체 제외용
    CATEGORY_INSTRUMENT_KEYWORDS = [
        'electric guitar', 'acoustic guitar', 'bass guitar',
        '일렉기타', '일렉트릭 기타', '어쿠스틱', '베이스기타'
    ]

    # BASS/GUITAR 검색 시 어쿠스틱 제외용 (일렉 위주 결과)
    CATEGORY_ACOUSTIC_KEYWORDS = [
        # 영문 - 베이스
        'acoustic bass', 'acoustic-electric bass', 'acousticbass', 'semi-acoustic bass',
        'hollow body bass', 'semi-hollow bass',
        'acoustic/electric', 'acoustic / electric', 'laurel', 'FA-450CE', 'CB-60SCE', 'Acoustic', 'kingman',
        # 독일어/프랑스어 등
        'akustikbass', 'akustik bass', 'acoustique basse',
        # 한글
        '어쿠스틱베이스', '어쿠스틱 베이스', '통베이스', '통기타베이스',
        # 영문 - 기타
        'acoustic guitar', 'acoustic-electric', 'semi-acoustic', 'hollow body',
        'semi-hollow', 'acousticguitar', 'akustikgitarre',
        # 한글 - 기타
        '어쿠스틱기타', '어쿠스틱 기타', '통기타'
    ]