"""
WSGI config for save_tool project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import os
import sys

filePath = os.path.dirname(os.path.abspath(__file__))
projPath = os.path.abspath(os.path.join(filePath, os.pardir))
if not projPath in sys.path:
    sys.path.insert(0, projPath)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "am_tools.settings")

application = get_wsgi_application()