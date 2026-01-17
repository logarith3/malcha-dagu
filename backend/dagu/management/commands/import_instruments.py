"""
악기 데이터 CSV Import 커맨드.

Usage:
    python manage.py import_instruments data/instruments.csv
    python manage.py import_instruments data/instruments.csv --update
    python manage.py import_instruments data/instruments.csv --dry-run
"""

import csv
from django.core.management.base import BaseCommand, CommandError
from dagu.models import Instrument


class Command(BaseCommand):
    help = 'CSV 파일에서 악기 데이터 import'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='CSV 파일 경로'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='기존 데이터 업데이트 (기본: 중복 스킵)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 저장 없이 테스트만 수행'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        update_existing = options['update']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN 모드 (실제 저장 안 함)\n'))

        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                # 필수 컬럼 체크
                required = {'brand', 'name'}
                if not required.issubset(reader.fieldnames or []):
                    raise CommandError(f'필수 컬럼 누락: {required - set(reader.fieldnames or [])}')

                stats = {'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

                for row_num, row in enumerate(reader, start=2):
                    try:
                        result = self._process_row(row, update_existing, dry_run)
                        stats[result] += 1
                    except Exception as e:
                        stats['errors'] += 1
                        self.stdout.write(
                            self.style.ERROR(f'❌ 행 {row_num}: {e}')
                        )

                self._print_summary(stats)

        except FileNotFoundError:
            raise CommandError(f'파일을 찾을 수 없습니다: {csv_file}')
        except UnicodeDecodeError:
            raise CommandError('파일 인코딩 오류. UTF-8로 저장해주세요.')

    def _process_row(self, row, update_existing, dry_run):
        """단일 행 처리"""
        brand = row['brand'].strip().lower()
        name = row['name'].strip().lower()

        if not brand or not name:
            raise ValueError('brand와 name은 필수입니다')

        # 카테고리 유효성 검사
        category = row.get('category', 'guitar').strip().lower()
        valid_categories = dict(Instrument.CATEGORY_CHOICES).keys()
        if category not in valid_categories:
            category = 'guitar'

        # 가격 파싱 (콤마 제거)
        price_str = row.get('reference_price', '0').replace(',', '').strip()
        reference_price = int(price_str) if price_str.isdigit() else 0

        data = {
            'category': category,
            'reference_price': reference_price,
            'image_url': row.get('image_url', '').strip(),
            'description': row.get('description', '').strip(),
        }

        existing = Instrument.objects.filter(brand=brand, name=name).first()

        if existing:
            if update_existing:
                if not dry_run:
                    for key, value in data.items():
                        setattr(existing, key, value)
                    existing.save()
                self.stdout.write(f'🔄 업데이트: {brand} {name}')
                return 'updated'
            else:
                self.stdout.write(self.style.WARNING(f'⏭️  스킵 (이미 존재): {brand} {name}'))
                return 'skipped'
        else:
            if not dry_run:
                Instrument.objects.create(brand=brand, name=name, **data)
            self.stdout.write(self.style.SUCCESS(f'✅ 생성: {brand} {name}'))
            return 'created'

    def _print_summary(self, stats):
        """결과 요약 출력"""
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f"✅ 생성: {stats['created']}개"))
        self.stdout.write(self.style.WARNING(f"🔄 업데이트: {stats['updated']}개"))
        self.stdout.write(f"⏭️  스킵: {stats['skipped']}개")
        if stats['errors']:
            self.stdout.write(self.style.ERROR(f"❌ 오류: {stats['errors']}개"))
        self.stdout.write('=' * 50)
