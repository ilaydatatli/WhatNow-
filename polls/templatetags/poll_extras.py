from django import template
from django.utils import timezone
from django.utils.timesince import timesince

register = template.Library()


@register.filter
def ago(value):
    """Short Turkish relative time, e.g. "3 saat önce"."""
    if (timezone.now() - value).total_seconds() < 60:
        return "az önce"
    return f"{timesince(value, depth=1)} önce"
