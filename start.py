import os
import subprocess
import threading
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialmediaproject.settings')
os.environ.setdefault('DEBUG', 'True')
os.environ.setdefault('ALLOWED_HOSTS', 'localhost,127.0.0.1')
os.environ.setdefault('REDIS_URL', '')

from django.core.management.utils import get_random_secret_key  # noqa: E402

os.environ.setdefault('SECRET_KEY', get_random_secret_key())

import django

django.setup()


def open_browser():
    time.sleep(4)
    subprocess.Popen(['cmd', '/c', 'start', '', 'http://127.0.0.1:8000/'])


threading.Thread(target=open_browser, daemon=True).start()

from django.core.management import call_command  # noqa: E402

call_command('runserver', '0.0.0.0:8000')
