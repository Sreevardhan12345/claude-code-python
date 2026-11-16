import string


class SafeFormatter(string.Formatter):
    def get_value(self, key, args, kwargs):
        # If the placeholder is a positional index (e.g., {0}, {1})
        if isinstance(key, int):
            try:
                return args[key]
            except IndexError:
                return ""
        # Fallback for keyword arguments (e.g., {name})
        return kwargs.get(key, "")


def safe_format(template, *args, **kwargs):
    return SafeFormatter().format(template, *args, **kwargs)
