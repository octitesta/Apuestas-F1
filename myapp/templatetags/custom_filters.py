from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Permite acceder a un item de un diccionario usando una clave dinámica
    Uso: {{ mi_dict|get_item:clave }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)