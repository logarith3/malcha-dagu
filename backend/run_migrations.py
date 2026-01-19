
import os
import django
from django.core.management import call_command
import sys

# Add the current directory (backend) to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

print("1. Making migrations for 'dagu'...")
call_command('makemigrations', 'dagu')

print("2. Applying migrations...")
call_command('migrate', 'dagu')

print("3. Done!")
