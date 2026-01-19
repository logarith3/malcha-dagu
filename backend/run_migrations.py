
import os
import django
from django.core.management import call_command

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

print("1. Making migrations for 'dagu'...")
call_command('makemigrations', 'dagu')

print("2. Applying migrations...")
call_command('migrate', 'dagu')

print("3. Done!")
