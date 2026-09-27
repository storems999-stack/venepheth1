from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Updates the current URL query parameters with the given kwargs.
    Example: {% url_replace page=2 %}
    """
    request = context.get('request')
    if not request:
        return ''
    query = request.GET.copy()
    for k, v in kwargs.items():
        query[k] = v
    return f"?{query.urlencode()}"
