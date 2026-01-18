"""
Celery tasks for MALCHA-DAGU.
Scheduled tasks for automatic cleanup.
"""

import logging

from celery import shared_task
from django.utils import timezone

from .models import ItemClick, UserItem

logger = logging.getLogger(__name__)


@shared_task(name='dagu.cleanup_expired_items')
def cleanup_expired_items():
    """
    만료된 매물 자동 비활성화.
    Celery Beat로 10분마다 실행.
    
    Soft Delete: is_active = False
    (실제 삭제는 하지 않음 - 데이터 보존)
    """
    now = timezone.now()
    
    # 만료되었지만 아직 활성 상태인 항목 조회
    expired_items = UserItem.objects.filter(
        is_active=True,
        expired_at__lte=now,
    )
    
    count = expired_items.count()
    
    if count > 0:
        # 일괄 업데이트 (효율적)
        expired_items.update(is_active=False)
        logger.info(f"Deactivated {count} expired items")
    else:
        logger.debug("No expired items to cleanup")
    
    return f"Processed {count} items"


@shared_task(name='dagu.purge_old_inactive_items')
def purge_old_inactive_items(days=30):
    """
    오래된 비활성 매물 완전 삭제.
    월 1회 정도 실행 권장.
    
    Args:
        days: 비활성화 후 며칠이 지난 항목을 삭제할지
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    old_items = UserItem.objects.filter(
        is_active=False,
        updated_at__lte=cutoff_date,
    )
    
    count = old_items.count()
    
    if count > 0:
        old_items.delete()
        logger.info(f"Purged {count} old inactive items")
    
    return f"Purged {count} items"


@shared_task(name='dagu.cleanup_old_click_logs')
def cleanup_old_click_logs(days=7):
    """
    오래된 클릭 로그 삭제.
    DB 용량 관리를 위해 7일 지난 로그 삭제.
    매일 1회 실행 권장.

    Args:
        days: 며칠 지난 클릭 로그를 삭제할지 (기본: 7일)
    """
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=days)

    old_clicks = ItemClick.objects.filter(clicked_at__lt=cutoff_date)
    count = old_clicks.count()

    if count > 0:
        old_clicks.delete()
        logger.info(f"Deleted {count} old click logs (older than {days} days)")
    else:
        logger.debug("No old click logs to cleanup")

    return f"Deleted {count} click logs"
