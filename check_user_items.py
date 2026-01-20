
import os
import django
from django.utils import timezone
from django.db.models import Q

import sys
sys.path.append('backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from dagu.models import UserItem, Instrument

print("\n=== LATEST 5 USER ITEMS ===")
last_items = UserItem.objects.order_by('-created_at')[:5]
for item in last_items:
    print(f"[Item ID: {item.id}]")
    print(f" - Title: {item.title}")
    print(f" - Price: {item.price}")
    print(f" - Instrument: {item.instrument}")
    print(f" - Created At: {item.created_at}")
    print(f" - Is Active: {item.is_active}")
    print("--------------------------------")
