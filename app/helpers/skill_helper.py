import re
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
    template = re.sub(r"\$(\d+)", r"{\1}", template)
    template = re.sub(r"\$ARGUMENTS\[(\d+)\]", r"{\1}", template)
    template = re.sub(r"\$ARGUMENTS", " ".join(args), template)
    return SafeFormatter().format(template, *args, **kwargs)


def split_skills_from_arguments(arguments: str):
    """Split the argument string into list of skills and list of arguments"""
    parts = arguments.split() if arguments else []
    skills = []
    args = []
    for i, part in enumerate(parts):
        if part.startswith("/"):
            skills.append(part)
        else:
            args = parts[i:]
            break
    return skills, args
