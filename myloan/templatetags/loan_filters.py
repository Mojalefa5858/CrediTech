from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def filter_status(queryset, status):
    """Filter a queryset by status."""
    return queryset.filter(status=status)

@register.filter
def div(value, arg):
    """Divide the value by the argument."""
    try:
        value = Decimal(str(value))
        arg = Decimal(str(arg))
        if arg == 0:
            return value
        return value / arg
    except (ValueError, TypeError, ZeroDivisionError):
        return value