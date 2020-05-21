class Cookie(object):
    def __init__(self, key, value=None, **kwargs):
        self.key = key
        self.value = value
        self.settings = kwargs