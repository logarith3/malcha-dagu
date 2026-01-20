
import os
import django
import sys

sys.path.append('backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from dagu.models import UserItem, Instrument
from django.db.models import Q

query = "ds-1"

with open("debug_result.txt", "w", encoding="utf-8") as f:
    f.write(f"Query: {query}\n")
    
    # 1. Check Instrument
    instruments = Instrument.objects.filter(name__icontains=query)
    f.write(f"Matching Instruments count: {instruments.count()}\n")
    inst_ids = []
    for inst in instruments:
        f.write(f"  Inst: {inst.id} | {inst.brand} | {inst.name}\n")
        inst_ids.append(inst.id)
        
    # 2. Check Latest UserItems
    f.write("\nLatest 5 UserItems:\n")
    latest = UserItem.objects.all().order_by('-created_at')[:5]
    for item in latest:
        f.write(f"  Item: {item.id} | Title: {item.title}\n")
        if item.instrument:
            f.write(f"    Linked Inst: {item.instrument.id} | {item.instrument.brand} | {item.instrument.name}\n")
            if item.instrument.id in inst_ids:
                f.write("    -> MATCHES matching_instrument!\n")
            else:
                f.write("    -> DOES NOT match matching_instrument ID.\n")
        else:
            f.write("    Linked Inst: None\n")
            
    # 3. Check Filter Query result
    q_filter = Q(instrument__name__icontains=query) | \
               Q(instrument__brand__icontains=query) | \
               Q(title__icontains=query)
    
    if instruments:
        q_filter |= Q(instrument__in=instruments)
        
    count = UserItem.objects.filter(q_filter).count()
    f.write(f"\nUserItem filter count: {count}\n")
