from django.utils import simplejson


def dump(obj, fp):
    return simplejson.dump(obj, fp)


def loads(s):
    return simplejson.loads(s)