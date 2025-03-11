# afrimeals_project/__init__.py
from __future__ import absolute_import, unicode_literals
from dashboard.celery import app as celery_app

__all__ = ('celery_app',)