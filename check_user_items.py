
import os
import django
from django.utils import timezone
from django.db.models import Q
import sys

sys.path.append('backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from dagu.models import UserItem, Instrument

query = "sm57"
print(f"Checking UserItems significantly related to '{query}'...")

# 1. Check Instrument Match
matching_instruments = Instrument.objects.filter(name__icontains=query)
print(f"Matching Instruments: {matching_instruments.count()}")
matching_ids = []
for inst in matching_instruments:
    print(f" - Found Instrument: {inst.brand} {inst.name} (ID: {inst.id})")
    matching_ids.append(inst.id)

# 2. Check UserItems with simplified query logic (mimicking search.py update)
q_filter = Q(instrument__name__icontains=query) | \
           Q(instrument__brand__icontains=query) | \
           Q(title__icontains=query)

if matching_instruments:
    q_filter |= Q(instrument__in=matching_instruments)

print(f"\nQuery Filter: {q_filter}")

items = UserItem.objects.filter(q_filter)
print(f"\nTotal UserItems matching query: {items.count()}")

# 3. Inspect Latest Items specifically for ID mismatch
print("\n=== LATEST 5 USER ITEMS INSPECTION ===")
last_items = UserItem.objects.order_by('-created_at')[:5]
for item in last_items:
    print(f"[Item ID: {item.id}]")
    print(f" - Title: {item.title}")
    print(f" - Instrument: {item.instrument} (ID: {item.instrument.id})")
    
    is_id_match = item.instrument.id in matching_ids
    print(f" - Included in Matching IDs? {is_id_match}")
            
    is_text_match = (
        query.lower() in item.title.lower() or 
        query.lower() in item.instrument.name.lower() or 
        query.lower() in item.instrument.brand.lower()
    )
    print(f" - Text match with '{query}'? {is_text_match}")
    print(f" - Is Active: {item.is_active}")
    print("--------------------------------")
