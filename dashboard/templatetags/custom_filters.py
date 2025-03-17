# dashboard/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get an item from a dictionary using bracket notation."""
    if dictionary is None:
        return ''
    return dictionary.get(key, '')