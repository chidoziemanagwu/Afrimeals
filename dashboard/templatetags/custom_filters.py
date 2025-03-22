# dashboard/templatetags/custom_filters.py
from django import template
import json


register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get an item from a dictionary using bracket notation."""
    if dictionary is None:
        return ''
    return dictionary.get(key, '')

@register.filter(name='to_json')
def to_json(value):
    return json.dumps(value)

# templatetags/custom_filters.py

@register.filter(name='format_style')
def format_style(value):
    """Convert style name to readable format"""
    return value.replace('_', ' ').title()