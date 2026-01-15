from django.db.models import Q, Value, CharField
from django.db.models.functions import Concat
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import statistics
import logging

from .models import Instrument, MarketPrice
from .serializers import InstrumentSerializer
# [중요] fetch_naver_data 포함, get_final_category 임포트
from .services import fetch_reverb_data, fetch_naver_data, get_final_category
from .utils import parse_brand_and_model

logger = logging.getLogger(__name__)


# =========================================================
# [1] CollectPriceAPI: 외부 데이터 수집용
# =========================================================
class CollectPriceAPI(APIView):
    """
    [POST] 외부(배치 프로그램 등)에서 수집한 데이터를 대량으로 업데이트할 때 사용
    """

    def post(self, request):
        if request.headers.get('Authorization') != settings.DAGU_API_KEY:
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        for item in data:
            instrument, _ = Instrument.objects.get_or_create(
                model_name=item['model_name'],
                defaults={'brand': item['brand'], 'image_url': item.get('image_url')}
            )

            MarketPrice.objects.update_or_create(
                instrument=instrument,
                shop_name=item['shop_name'],
                is_used=item.get('is_used', False),
                defaults={
                    'price': item['price'],
                    'deal_url': item['deal_url']
                }
            )
        return Response({"message": "데이터 업데이트 성공!"}, status=status.HTTP_200_OK)


# =========================================================
# [2] DaguSearchAPI: 악기 검색 및 신규 생성용
# =========================================================
class DaguSearchAPI(APIView):
    """
    [GET] 통합 검색 API
    """

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return Response([])

        instruments = Instrument.objects.annotate(
            full_name=Concat('brand', Value(' '), 'model_name', output_field=CharField())
        ).filter(
            Q(full_name__icontains=query) |
            Q(brand__icontains=query) |
            Q(model_name__icontains=query)
        )

        if not instruments.exists():
            if len(query) < 2:
                return Response([])

            brand, model_name = parse_brand_and_model(query)
            if not brand:
                brand = "Pending..."

            new_instrument = Instrument.objects.create(
                brand=brand,
                model_name=model_name,
                category='PENDING'
            )
            instruments = [new_instrument]

        serializer = InstrumentSerializer(instruments, many=True)
        return Response(serializer.data)


# =========================================================
# [3] InstrumentPriceDetailAPI: 시세 상세 및 실시간 크롤링
# =========================================================
class InstrumentPriceDetailAPI(APIView):
    """
    [GET] 시세 상세 조회 (Reverb + Naver Shopping)
    """

    def get(self, request, instrument_id):
        try:
            instrument = Instrument.objects.get(id=instrument_id)
            final_category = get_final_category(instrument)

            logger.info(f"시세 조회 요청: [{final_category}] {instrument.brand} {instrument.model_name}")

            force_refresh = request.GET.get('force_refresh', '').lower() in ['true', '1', 'yes']

            # 1. 캐시 확인
            if not force_refresh:
                cache_limit = timezone.now() - timedelta(hours=12)
                cached_prices = MarketPrice.objects.filter(
                    instrument=instrument,
                    updated_at__gte=cache_limit
                )

                if cached_prices.count() >= 3:
                    unique_shops = cached_prices.values('shop_name').distinct().count()
                    if unique_shops >= 2:
                        return Response({
                            'status': 'success',
                            'source': 'cache',
                            'instrument': str(instrument),
                            'prices': list(
                                cached_prices.values('shop_name', 'price', 'is_used', 'deal_url', 'updated_at'))
                        })

            # 2. 실시간 크롤링 (Reverb, Naver)
            updated_listings = []
            crawl_errors = {}

            # (1) Reverb
            try:
                reverb = fetch_reverb_data(instrument, category=final_category)
                if reverb:
                    updated_listings.extend(reverb)
                else:
                    crawl_errors['Reverb'] = '검색 결과 없음'
            except Exception as e:
                crawl_errors['Reverb'] = str(e)

            # (2) Naver
            try:
                naver = fetch_naver_data(instrument, category=final_category)
                if naver:
                    updated_listings.extend(naver)
                else:
                    crawl_errors['Naver'] = '검색 결과 없음'
            except Exception as e:
                crawl_errors['Naver'] = str(e)

            # 3. DB 동기화 및 자동 분류
            if updated_listings:
                MarketPrice.objects.filter(instrument=instrument).delete()

                if instrument.category == 'PENDING':
                    prices = [item['price'] for item in updated_listings]
                    median_price = statistics.median(prices)
                    model_lower = instrument.model_name.lower()

                    if any(kw in model_lower for kw in
                           ['pedal', 'stomp', 'overdrive', 'delay']) or median_price < 350000:
                        instrument.category = 'PEDAL'
                    elif 'bass' in model_lower:
                        instrument.category = 'BASS'
                    else:
                        instrument.category = 'GUITAR'
                    instrument.save()

                # 벌크 생성
                price_objects = [
                    MarketPrice(
                        instrument=instrument,
                        shop_name=entry['shop_name'],
                        price=entry['price'],
                        is_used=entry['is_used'],
                        deal_url=entry['deal_url']
                    ) for entry in updated_listings
                ]
                MarketPrice.objects.bulk_create(price_objects)

            # 4. 결과 반환
            final_prices = MarketPrice.objects.filter(instrument=instrument).order_by('price')

            return Response({
                'status': 'success' if updated_listings else 'no_results',
                'source': 'live',
                'instrument': str(instrument),
                'prices': list(final_prices.values('shop_name', 'price', 'is_used', 'deal_url', 'updated_at')),
                'crawl_errors': crawl_errors if crawl_errors else None
            })

        except Instrument.DoesNotExist:
            return Response({"error": "Instrument not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"서버 오류: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)