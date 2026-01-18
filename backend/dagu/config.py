"""
Filter configuration for MALCHA-DAGU.
Based on proven filtering patterns for instrument search quality.
"""


class CrawlerConfig:
    """크롤러/API 설정"""

    # 가격 설정 (신품 기준가 없을 때 폴백용)
    MIN_PRICE_KRW = 200000  # 20만원 (악기 기본)
    MIN_PRICE_PEDAL = 50000 # 5만원 (이펙터/액세서리)
    MIN_PRICE_MIC = 30000   # 3만원 (마이크)
    MIN_PRICE_USD = 100

    # 신품 기준가 대비 최소가 비율 (45% = 0.45)
    MIN_PRICE_RATIO = 0.45
    
    # 결과 개수 설정
    MAX_RESULTS_NAVER = 20
    MAX_RESULTS_USER = 20
    
    # 타임아웃
    TIMEOUT_NAVER = 5


class CategoryConfig:
    """카테고리 판별용 키워드"""

    # =========================================================================
    # 1. 브랜드/카테고리 리스트 확장
    # =========================================================================

    GUITAR_BRANDS = [
        "fender", "gibson", "prs", "ibanez", "esp", "jackson", "gopherwood", "swing",
        "schecter", "suhr", "tom anderson", "james tyler", "mayones", "strandberg",
        "cort", "yamaha", "epiphone", "squier", "ltd", "musicman", "gretsch"
    ]

    BASS_KEYWORDS = [
        'bass', 'precision', 'jazz bass', 'pbass', 'jbass',
        '베이스', '베이쓰', '프레시전', '프레시젼', '재즈베이스', '재베', '프베',
        'stingray', '스팅레이', 'sire', '사이어', 'fami', '액티브', '패시브'
    ]

    # =========================================================================
    # 2. 모델명 별칭 매핑 (검색어 → 정식 모델명)
    # =========================================================================
    MODEL_ALIASES = {
        # --- Fender & Squier (국내 은어 포함) ---
        'strat': 'Stratocaster',
        'stratocaster': 'Stratocaster',
        '스트랫': 'Stratocaster',
        '스트렛': 'Stratocaster',
        '스트라토캐스터': 'Stratocaster',
        '스텐다드': 'Standard',
        '스탠다드': 'Standard',
        'tele': 'Telecaster',
        'telecaster': 'Telecaster',
        '텔레': 'Telecaster',
        '텔레캐스터': 'Telecaster',
        'jazzmaster': 'Jazzmaster',
        '재즈마스터': 'Jazzmaster',
        '재마': 'Jazzmaster',
        'jaguar': 'Jaguar',
        '재규어': 'Jaguar',
        'mustang': 'Mustang',
        '머스탱': 'Mustang',
        '미펜': 'Fender American',  # 중요: 원산지 은어
        '일펜': 'Fender Japan',
        '멕펜': 'Fender Mexico',
        '커샵': 'Custom Shop',
        '커스텀샵': 'Custom Shop',
        '트레디셔널': 'Traditional',
        '트레': 'Traditional',
        '프로페셔널': 'Professional',
        '아프로': 'American Professional',
        '울트라': 'Ultra',
        '빈티지': 'Vintage',
        '리이슈': 'Reissue',

        # --- Gibson & Epiphone ---
        'lp': 'Les Paul',
        'lespaul': 'Les Paul',
        'les paul': 'Les Paul',
        '레스폴': 'Les Paul',
        '레폴': 'Les Paul',  # 은어
        'sg': 'SG',
        '에스지': 'SG',
        'es335': 'ES-335',
        'es-335': 'ES-335',
        '할로우': 'Hollow Body',
        '세미할로우': 'Semi-Hollow',
        'flying v': 'Flying V',
        '플라잉브이': 'Flying V',
        'explorer': 'Explorer',
        '익스플로러': 'Explorer',
        'j45': 'J-45',
        'hummingbird': 'Hummingbird',
        '허밍버드': 'Hummingbird',
        '히스토릭': 'Historic',
        '트래디셔널': 'Traditional',

        # --- Ibanez & Super Strat ---
        'rg': 'RG',
        'az': 'AZ',
        'jem': 'JEM',
        'prestige': 'Prestige',
        '프레스티지': 'Prestige',
        'j.custom': 'j.custom',
        '제이커스텀': 'j.custom',
        'pia': 'PIA',

        # --- PRS ---
        'custom24': 'Custom 24',
        'custom 24': 'Custom 24',
        '커스텀24': 'Custom 24',
        'mccarty': 'McCarty',
        '매카티': 'McCarty',
        'silver sky': 'Silver Sky',
        '실버스카이': 'Silver Sky',
        '실스': 'Silver Sky',  # 은어
        'se': 'SE',
        'ce': 'CE',

        # --- BOSS Pedals (상세 매핑) ---
        'ds1': 'DS-1', 'ds-1': 'DS-1',
        'ds2': 'DS-2', 'ds-2': 'DS-2',
        'sd1': 'SD-1', 'sd-1': 'SD-1',
        'bd2': 'BD-2', 'bd-2': 'BD-2',
        'mt2': 'MT-2', 'mt-2': 'MT-2',
        'od3': 'OD-3', 'od-3': 'OD-3',
        'ce5': 'CE-5', 'ce-5': 'CE-5',
        'ch1': 'CH-1', 'ch-1': 'CH-1',
        'dd8': 'DD-8', 'dd-8': 'DD-8',
        'dd200': 'DD-200', 'dd-200': 'DD-200',
        'rv6': 'RV-6', 'rv-6': 'RV-6',
        'tu3': 'TU-3', 'tu-3': 'TU-3',
        'rc5': 'RC-5', 'rc-5': 'RC-5',
        'gt1000': 'GT-1000', 'gt-1000': 'GT-1000',
        'katana': 'KATANA',

        # --- Popular Pedals & Multi-FX (은어 포함) ---
        'ts9': 'TS9',
        'ts808': 'TS808',
        'tubescreamer': 'Tube Screamer',
        'tube screamer': 'Tube Screamer',
        '튜브스크리머': 'Tube Screamer',
        'bigsky': 'BigSky',
        '빅스카이': 'BigSky',
        'timeline': 'Timeline',
        '타임라인': 'Timeline',
        'mobius': 'Mobius',
        '모비우스': 'Mobius',
        'blue sky': 'BlueSky',
        '블루스카이': 'BlueSky',
        'h9': 'H9',
        'helix': 'Helix',
        '힐릭스': 'Helix',
        'hx stomp': 'HX Stomp',
        'hxstomp': 'HX Stomp',
        'hx스톰프': 'HX Stomp',
        'quad cortex': 'Quad Cortex',
        '쿼드코텍스': 'Quad Cortex',
        '쿼드코어텍스': 'Quad Cortex',  # 오타 대응
        '쿼코': 'Quad Cortex',  # 은어
        'kemper': 'Kemper',
        '켐퍼': 'Kemper',
        '캠퍼': 'Kemper',
        'iridium': 'Iridium',
        '이리듐': 'Iridium',
        'ocd': 'OCD',
        'klon': 'Centaur',
        'centaur': 'Centaur',
        '클론': 'Centaur',
        'jan ray': 'Jan Ray',
        '잔레이': 'Jan Ray',
        'timmy': 'Timmy',
        '팀미': 'Timmy',

        # --- Bass Specific ---
        '베이스': 'bass',
        'pbass': 'Precision Bass',
        'p-bass': 'Precision Bass',
        'precision': 'Precision Bass',
        '프레시전': 'Precision Bass',
        '프레시젼': 'Precision Bass',
        '프베': 'Precision Bass',
        'jbass': 'Jazz Bass',
        'j-bass': 'Jazz Bass',
        '재즈베이스': 'Jazz Bass',
        '재베': 'Jazz Bass',
        'stingray': 'StingRay',
        '스팅레이': 'StingRay',

        # --- Amps ---
        'jcm800': 'JCM800',
        'jcm900': 'JCM900',
        'jcm2000': 'JCM2000',
        'dsl': 'DSL',
        'plexi': 'Plexi',
        '플렉시': 'Plexi',
        'ac30': 'AC30',
        'ac15': 'AC15',
        'twin reverb': 'Twin Reverb',
        '트윈리버브': 'Twin Reverb',
        'blues junior': 'Blues Junior',
        '블루스주니어': 'Blues Junior',
        '블주': 'Blues Junior',  # 은어
        'rectifier': 'Rectifier',
        '렉티파이어': 'Rectifier',
        'mark v': 'Mark V',
        '마크5': 'Mark V',

        # --- General Terms ---
        '기타': 'guitar',
        '일렉': 'electric',
        '어쿠스틱': 'acoustic',
        '통기타': 'acoustic guitar',
        '멀펙': 'Multi Effect',  # 은어
        '멀티이펙터': 'Multi Effect',
        '꾹꾹이': 'Stompbox',  # 은어
    }

    # =========================================================================
    # 3. 키워드 리스트 확장 (검색 필터링용)
    # =========================================================================

    PEDAL_KEYWORDS = [
        'pedal', 'stomp', 'effect', 'effects', 'effector', 'processor',
        '이펙터', '페달', '스톰프', '꾹꾹이', '멀티이펙터', '멀펙', '보드',
        # 브랜드
        'boss', '보스', 'strymon', '스트라이몬', 'tc electronic', '티씨',
        'mxr', 'electro-harmonix', 'ehx', '이하모',
        'ibanez', 'ts808', 'ts9', 'keeley', '킬리', 'walrus', '월러스', 'jhs',
        'chase bliss', '체이스블리스', 'vemuram', '베무람', 'xotic', '엑조틱',
        'universal audio', 'ua', 'line6', '라인6', 'neural dsp', '뉴럴',
        # 이펙트 종류 (한글 포함)
        'overdrive', '오버드라이브', 'distortion', '디스토션', 'fuzz', '퍼즈',
        'delay', '딜레이', 'reverb', '리버브', 'chorus', '코러스', 'phaser', '페이저',
        'flanger', '플랜저', 'compressor', '컴프', '컴프레서', 'wah', '와우',
        'looper', '루퍼', 'tuner', '튜너', 'eq', '이퀄라이저',
        'booster', '부스터', 'octave', '옥타브', 'tremolo', '트레몰로',
        'vibrato', '비브라토', 'noise gate', '노이즈게이트', 'preamp', '프리앰프',
        'ir loader', 'ir로더', 'cab sim', '캡심',
        # 주요 모델 식별자
        'ds-1', 'sd-1', 'bd-2', 'mt-2', 'ts9', 'ts808', 'klon', 'ocr', 'bigsky',
        'h9', 'hx stomp', 'quad cortex', 'gt-1000', 'kemper'
    ]

    AMP_KEYWORDS = [
        'amp', 'cabinet', 'head', 'combo', 'amplifier', 'stack',
        '앰프', '캐비넷', '캐비닛', '헤드', '콤보', '스택', '진공관', '튜브',
        'tube amp', 'solid state', '솔리드스테이트', 'modeling', '모델링',
        'marshall', '마샬', 'fender', '펜더', 'vox', '복스', 'orange', '오렌지',
        'mesa boogie', '메사', '메사부기', 'kemper', '캠퍼', 'fractal', '프랙탈',
        'yamaha thr', 'thr10', 'thr30', 'katana', '카타나', 'spark', '스파크'
    ]

    ACOUSTIC_KEYWORDS = [
        'acoustic', 'martin', 'taylor', 'gibson', 'yamaha', 'cort', 'crafter',
        '어쿠스틱', '통기타', '마틴', '테일러', '야마하', '콜트', '크래프터', '고퍼우드',
        'top solid', '탑솔리드', 'all solid', '올솔리드', '탑백솔리드',
        'dreadnought', '드레드넛', 'om body', 'om바디', 'ga body', 'ga바디',
        'jumbo', '점보', 'parlor', '팔러', 'cutaway', '컷어웨이', 'pickup', '픽업'
    ]

    MIC_KEYWORDS = [
        'microphone', 'mic', 'condenser', 'dynamic', 'ribbon', 'wireless',
        '마이크', '마이크로폰', '콘덴서', '다이나믹', '리본', '무선',
        # 브랜드
        'shure', '슈어', 'sennheiser', '젠하이저', 'neumann', '노이만',
        'akg', 'audio-technica', '오디오테크니카', 'rode', '로데',
        'blue', 'beyerdynamic', '베이어다이나믹', 'electro-voice', 'ev',
        'warm audio', '웜오디오', 'lewitt', '루윗',
        # 모델
        'sm58', 'sm57', 'sm7b', 'beta58', 'u87', 'tlm103', 'nt1', 'at2020',
    ]
    # 알려진 브랜드 목록 (브랜드 감지용)
    KNOWN_BRANDS = [
        # ---------------------------------------------------------
        # 1. Electric Guitars (Major & High-end)
        # ---------------------------------------------------------
        'fender', 'gibson', 'prs', 'ibanez', 'esp', 'jackson', 'charvel',
        'schecter', 'suhr', 'musicman', 'g&l', 'yamaha', 'kramer',
        'gretsch', 'rickenbacker', 'danelectro', 'tom anderson', 'james tyler',
        'mayones', 'strandberg', 'aristides', 'kiesel', 'godin', 'reverend',
        'duesenberg', 'heritage', 'bacchus', 'momose', 'fgn',  # Fujigen

        # ---------------------------------------------------------
        # 2. Sub & Budget Brands (Cost-effective)
        # ---------------------------------------------------------
        'squier', 'epiphone', 'ltd', 'sterling', 'tribute', 'edwards',
        'grassroots', 'tokai', 'burny', 'greco', 'aria pro ii',
        'harley benton', 'sire', 'cort', 'swing', 'dame', 'hex', 'spear',
        'uno', 'corona', 'volcan',

        # ---------------------------------------------------------
        # 3. Acoustic Guitars
        # ---------------------------------------------------------
        'taylor', 'martin', 'gopherwood', 'crafter', 'lakewood', 'maton',
        'cole clark', 'sigma', 'guild', 'takamine', 'ovation', 'lowden',
        'mcpherson', 'breedlove', 'seagull', 'yamaha', 'cort',

        # ---------------------------------------------------------
        # 4. Bass Specific (High-end & Popular)
        # ---------------------------------------------------------
        'warwick', 'spector', 'sandberg', 'dingwall', 'fodera', 'sadowsky',
        'lakland', 'mtd', 'kensmith', 'atelier z', 'moon',

        # ---------------------------------------------------------
        # 5. Amps & Modelers (Digital/Analog)
        # ---------------------------------------------------------
        'marshall', 'vox', 'orange', 'mesa', 'ampeg', 'fender', 'peavey',
        'engl', 'bogner', 'friedman', 'soldano', 'blackstar', 'hughes & kettner',
        'kemper', 'fractal', 'line 6', 'neural dsp', 'headrush', 'boss', 'roland',
        'positive grid', 'dv mark', 'markbass', 'aguilar', 'darkglass',

        # ---------------------------------------------------------
        # 6. Effects Pedals (Stompboxes)
        # ---------------------------------------------------------
        'boss', 'tc electronic', 'strymon', 'electro-harmonix', 'mxr', 'dunlop',
        'digitech', 'zoom', 'mooer', 'nux', 'jhs', 'keeley', 'walrus audio',
        'chase bliss', 'eventide', 'meris', 'earthquaker devices', 'analogman',
        'fulltone', 'xotic', 'vemuram', 'klon', 'catalinbread', 'mad professor',
        'source audio', 'free the tone', 'vertex', 'hotone', 'valeton',
    ]

    # 한글 브랜드명 매핑 (유저가 검색할 만한 변칙 표기 포함)
    BRAND_NAME_MAPPING = {
        # --- Major Guitars ---
        '펜더': 'fender', '팬더': 'fender',
        '깁슨': 'gibson',
        '피알에스': 'prs', '폴리드스미스': 'prs', '폴리드': 'prs',
        '아이바네즈': 'ibanez', '이바네즈': 'ibanez',
        '이에스피': 'esp',
        '잭슨': 'jackson',
        '샤벨': 'charvel',
        '쉑터': 'schecter', '섹터': 'schecter',
        '써': 'suhr', '서': 'suhr', '존써': 'suhr',
        '뮤직맨': 'musicman',
        '지앤엘': 'g&l', '지엔엘': 'g&l',
        '야마하': 'yamaha',
        '크래머': 'kramer', '크레이머': 'kramer',
        '그레치': 'gretsch',
        '리켄베커': 'rickenbacker', '리켄배커': 'rickenbacker',
        '댄일렉트로': 'danelectro', '댄일렉': 'danelectro',
        '탐앤더슨': 'tom anderson', '톰앤더슨': 'tom anderson',
        '제임스타일러': 'james tyler', '제타': 'james tyler',
        '마요네즈': 'mayones',
        '스트랜드버그': 'strandberg',
        '아리스티데스': 'aristides',
        '키젤': 'kiesel', '카이젤': 'kiesel',
        '고딘': 'godin',
        '레버런드': 'reverend', '레버랜드': 'reverend',
        '듀센버그': 'duesenberg',
        '헤리티지': 'heritage',
        '바커스': 'bacchus', '바쿠스': 'bacchus',
        '모모세': 'momose',
        '후지겐': 'fgn',

        # --- Sub/Budget/Domestic ---
        '스콰이어': 'squier', '스퀴어': 'squier',
        '에피폰': 'epiphone',
        '엘티디': 'ltd',
        '스털링': 'sterling',
        '트리뷰트': 'tribute',
        '에드워즈': 'edwards',
        '그라스루츠': 'grassroots',
        '토카이': 'tokai',
        '버니': 'burny',
        '그레코': 'greco',
        '할리벤튼': 'harley benton',
        '사이어': 'sire',
        '콜트': 'cort',
        '스윙': 'swing',
        '데임': 'dame',
        '헥스': 'hex',
        '스피어': 'spear',
        '우노': 'uno',
        '코로나': 'corona',
        '볼캔': 'volcan', '볼칸': 'volcan',

        # --- Acoustic ---
        '테일러': 'taylor',
        '마틴': 'martin',
        '고퍼우드': 'gopherwood',
        '크래프터': 'crafter', '성음': 'crafter',
        '레이크우드': 'lakewood',
        '메이튼': 'maton',
        '콜클락': 'cole clark',
        '시그마': 'sigma',
        '길드': 'guild',
        '타카미네': 'takamine',
        '오베이션': 'ovation',
        '로우든': 'lowden',
        '맥퍼슨': 'mcpherson',
        '브리러브': 'breedlove',
        '시걸': 'seagull',

        # --- Bass Specific ---
        '워윅': 'warwick',
        '스펙터': 'spector',
        '샌드버그': 'sandberg',
        '딩월': 'dingwall',
        '포데라': 'fodera',
        '새도우스키': 'sadowsky', '새도스키': 'sadowsky',
        '락랜드': 'lakland', '레크랜드': 'lakland',
        '엠티디': 'mtd',
        '켄스미스': 'kensmith',
        '아틀리에': 'atelier z', '아틀리에지': 'atelier z',
        '문': 'moon',

        # --- Amps & Modelers ---
        '마샬': 'marshall',
        '복스': 'vox',
        '오렌지': 'orange',
        '메사': 'mesa', '메사부기': 'mesa',
        '암펙': 'ampeg', '암페그': 'ampeg',
        '피비': 'peavey',
        '앵글': 'engl', '이엔지에이': 'engl',
        '보그너': 'bogner',
        '프리드만': 'friedman',
        '솔다노': 'soldano',
        '블랙스타': 'blackstar',
        '휴거스앤케트너': 'hughes & kettner', '휴거스': 'hughes & kettner',
        '켐퍼': 'kemper',
        '프랙탈': 'fractal', '프렉탈': 'fractal',
        '라인식스': 'line 6', '라인6': 'line 6', '힐릭스': 'line 6',
        '뉴럴': 'neural dsp', '뉴럴디에스피': 'neural dsp', '쿼드코어텍스': 'neural dsp',
        '헤드러쉬': 'headrush', '헤드러시': 'headrush',
        '포지티브그리드': 'positive grid', '스파크': 'positive grid',
        '디브이마크': 'dv mark',
        '마크베이스': 'markbass',
        '아귈라': 'aguilar',
        '다크글래스': 'darkglass',

        # --- Pedals ---
        '보스': 'boss',
        '티씨': 'tc electronic', '티씨일렉트로닉': 'tc electronic',
        '스트라이몬': 'strymon', '스트라이먼': 'strymon',
        '일렉트로하모닉스': 'electro-harmonix', '이하모': 'electro-harmonix',
        '엠엑스알': 'mxr',
        '던롭': 'dunlop',
        '디지텍': 'digitech',
        '줌': 'zoom',
        '무어': 'mooer',
        '눅스': 'nux',
        '제이에이치에스': 'jhs',
        '킬리': 'keeley',
        '월러스': 'walrus audio', '월러스오디오': 'walrus audio',
        '체이스블리스': 'chase bliss',
        '이븐타이드': 'eventide',
        '메리스': 'meris',
        '얼스퀘이커': 'earthquaker devices', '이큐디': 'earthquaker devices',
        '아날로그맨': 'analogman',
        '풀톤': 'fulltone',
        '엑조틱': 'xotic', '에그조틱': 'xotic',
        '베무람': 'vemuram',
        '클론': 'klon',
        '카탈린브레드': 'catalinbread',
        '매드프로페서': 'mad professor',
        '소스오디오': 'source audio',
        '프리더톤': 'free the tone',
        '버텍스': 'vertex',
        '핫톤': 'hotone',
        '발레톤': 'valeton',
    }
    
  

class FilterConfig:
    """필터링 설정"""

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
        '넥만', '바디', '바디만', '픽업', '노브', '브릿지', '브리지',
        '부품', '나사', '너트', '키트', '조립', '배선', '픽가드', '스위치',
        '튜너', '커버', '덮개', '회로', '스피커', '알루미늄', '툴', '아노다이징', '튜닝', '본체',
        
        # 3. 액세서리류 (영문)
        'case', 'bag', 'gig bag', 'hardcase', 'strap', 'cable',
        'capo', 'hanger', 'sticker', 'picks', 'slide',
        'string', 'polish', 'cloth', 'mini', '미니', 'adapter', '모자', '자전거',  # '손잡이' 제거 (왼손잡이 기타 오탐 방지)
        
        # 3-1. 액세서리류 (한글)
        '케이스', '가방', '긱백', '스트랩', '케이블',
        '카포', '스탠드', '거치대', '슬라이드', '줄', '어댑터',
        
        # 4. 문서/잡동사니
        'manual', 'instruction', 'warranty', 'certificate', 'book',
        'logo', 'decal', 'poster', 'catalog',
        '설명서', '메뉴얼', '보증서', '교본', '로고', '포스터', '카트리지', '그릴', '마이크 솜', '티',
        
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
        # ---------------------------------------------------------
        # 1. Fender Family
        # ---------------------------------------------------------
        'fender': [
            # 서브 브랜드
            'squier', 'squire', '스콰이어', '스퀴어',
            # 보급형 시리즈 (Squier 라인업)
            'affinity', '어피니티', 'bullet', '불렛', 'sonic', '소닉',
            'classic vibe', 'cv', '클래식바이브', '클바',
            'paranormal', '파라노말', 'contemporary', '컨템포러리',
            'fender clone', 'copy', 'replica', '이미테이션', '짝퉁',
            'starcaster', '스타캐스터',  # Fender 서브 브랜드로 취급되기도 함
            'mini', '미니',  # 미니 기타
        ],

        # ---------------------------------------------------------
        # 2. Gibson Family
        # ---------------------------------------------------------
        'gibson': [
            # 서브 브랜드
            'epiphone', '에피폰',
            'maestro', '마에스트로',  # 초저가 라인
            'baldwin', '볼드윈',
            'kramer', '크래머',  # 현재는 Gibson 산하이나 독자 라인 성격 강함 (구분 필요 시 분리)
            'orville', '오빌',  # 과거 일본 생산 라이선스 브랜드
            'kalamazoo', '칼라마주',
            # 가품/카피
            'gibson style', 'gibson copy', 'replica', 'chibson', '짭슨', '레플리카',
        ],

        # ---------------------------------------------------------
        # 3. PRS (Paul Reed Smith)
        # ---------------------------------------------------------
        'prs': [
            # 보급형/임포트 라인
            'se', 'student edition', '에스이',
            's2', '에스투',  # *주의: S2는 USA 라인이지만 Core(메인)보다 저렴하여 구분하기도 함
            'ce', '씨이',  # *주의: CE(Bolt-on)도 USA지만 가격대가 다름
            'se standard', 'se custom',
        ],

        # ---------------------------------------------------------
        # 4. ESP Family
        # ---------------------------------------------------------
        'esp': [
            # 서브 브랜드 (가격대별)
            'ltd', '엘티디',
            'edwards', '에드워즈',  # 일본 내수 중급
            'grassroots', '그라스루츠',  # 일본 내수 보급형
            'navigator', '네비게이터',  # ESP보다 비싼 빈티지 복각 라인
        ],

        # ---------------------------------------------------------
        # 5. Music Man (Ernie Ball)
        # ---------------------------------------------------------
        'musicman': [
            # 서브 브랜드
            'sterling', 'sterling by musicman', 'sbmm', '스털링',
            'sub', 's.u.b', '서브',  # Sterling의 하위 라인
            'olp', '올피',  # 과거 라이선스 저가형 (중고 시장에 많음)
        ],

        # ---------------------------------------------------------
        # 6. G&L
        # ---------------------------------------------------------
        'g&l': [
            'tribute', 'tribute series', '트리뷰트',  # 인도네시아/중국 생산 라인
        ],

        # ---------------------------------------------------------
        # 7. Lakland
        # ---------------------------------------------------------
        'lakland': [
            'skyline', '스카이라인',  # 인도네시아 생산 라인
        ],

        # ---------------------------------------------------------
        # 8. Schecter
        # ---------------------------------------------------------
        'schecter': [
            'sgr', '에스지에이알',  # 초저가 입문용 라인
            'diamond series', '다이아몬드', '다이아몬드 시리즈',  # 대부분의 양산형 모델 (USA 커스텀과 구분)
            'omen', '오멘',
            'damien', '데미안',
        ],

        # ---------------------------------------------------------
        # 9. Warwick (Bass)
        # ---------------------------------------------------------
        'warwick': [
            'rockbass', 'rock bass', '락베이스',  # 저가형 라인
        ],

        # ---------------------------------------------------------
        # 10. Suhr
        # ---------------------------------------------------------
        'suhr': [
            'rasmus', '라스무스',  # 단종된 중국 생산 라인 (중고 시장에 가끔 등장)
        ],

        # ---------------------------------------------------------
        # 11. Marshall (Amps)
        # ---------------------------------------------------------
        'marshall': [
            'mg', 'mg series', '엠지',  # 저가형 TR 앰프 라인 (JCM/JVM 등 진공관과 구분)
            'park', '파크',  # 과거 마샬의 서브 브랜드
            'valvestate', '밸브스테이트',  # 구형 하이브리드
        ]
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

    # 이펙터 검색 시 확실한 이펙터 확인용
    EFFECT_CONFIRM_KEYWORDS = [
        'pedal', 'effect', 'stomp', '페달', '이펙터', '이펙트',
    ]

    # 마이크 검색 시 확실한 마이크 확인용
    MIC_CONFIRM_KEYWORDS = [
        'microphone', 'mic', 'condenser', 'dynamic', 'vocal',
        '마이크', '마이크로폰', '콘덴서', '다이나믹', '보컬',
    ]

    # 마이크 검색 시 제외할 키워드 (기타/베이스/앰프/이펙터)
    CATEGORY_MIC_EXCLUDE_KEYWORDS = [
        'guitar', 'bass', 'amp', 'amplifier', 'pedal', 'effect',
        '기타', '베이스', '앰프', '페달', '이펙터',
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
        '기타케이스', '베이스케이스', '긱백',
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
        'mic': ['마이크', '마이크로폰', '콘덴서마이크', '다이나믹마이크', '무선마이크'],
    }
    
    # =========================================================================
    # [8] productType 필터 (상품 타입별 신뢰도)
    # =========================================================================
    # 1: 일반상품(가격비교O), 2: 일반상품(가격비교X), 3: 일반상품(가격비교 매칭)
    # 4: 중고상품, 5: 단종상품, 6: 판매예정상품
    VALID_PRODUCT_TYPES = [1, 2, 3]  # 중고(4), 단종(5), 판매예정(6) 제외
