from django.conf import settings


def is_solr_supported():
    try:
        return
        # return "Solr" in settings.HAYSTACK_CONNECTIONS["default"]["ENGINE"]
    except (KeyError, AttributeError):
        return False


def is_elasticsearch_supported():
    try:
        return
        # return "Elasticsearch" in settings.HAYSTACK_CONNECTIONS["default"]["ENGINE"]
    except (KeyError, AttributeError):
        return False
