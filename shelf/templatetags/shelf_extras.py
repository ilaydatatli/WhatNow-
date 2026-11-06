from django import template
from django.utils import timezone
from django.utils.timesince import timesince

from shelf.models import status_label as _status_label

register = template.Library()


@register.filter
def ago(value):
    """Short Turkish relative time, e.g. "3 saat önce"."""
    if (timezone.now() - value).total_seconds() < 60:
        return "az önce"
    return f"{timesince(value, depth=1)} önce"


@register.filter
def stars(rating):
    """5-star text, e.g. 4 -> "★★★★☆"."""
    rating = round(rating or 0)
    return "★" * rating + "☆" * (5 - rating)


@register.simple_tag
def status_label(status, kind):
    return _status_label(status, kind)
