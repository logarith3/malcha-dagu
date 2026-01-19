
import os
import django
from django.utils.text import slugify

# Use local settings for script execution
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from dagu.models import Instrument, Brand

def populate_brands():
    print("Starting Brand population...")
    instruments = Instrument.objects.all()
    count = 0
    updated_count = 0
    
    # Unique brands found
    brands_found = set()
    
    for inst in instruments:
        count += 1
        brand_text = inst.brand
        if not brand_text:
            continue
            
        # Create/Get Brand
        brand_slug = slugify(brand_text)
        if not brand_slug:
             continue
             
        brand_obj, created = Brand.objects.get_or_create(
            slug=brand_slug,
            defaults={
                'name': brand_text.title(),
                'description': f"{brand_text.title()} 브랜드입니다."
            }
        )
        
        if created:
            print(f"Created Brand: {brand_obj.name}")
            brands_found.add(brand_obj.name)
        
        # Link Instrument
        if not inst.brand_obj:
            inst.brand_obj = brand_obj
            inst.save() # This triggers the save logic we added too
            updated_count += 1
            if updated_count % 10 == 0:
                print(f"Updated {updated_count} instruments...")

    print(f"Done! Processed {count} instruments, updated {updated_count} links.")
    print(f"Total Brands in DB: {Brand.objects.count()}")

if __name__ == "__main__":
    populate_brands()
