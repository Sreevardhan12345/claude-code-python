import yaml

with open("sample.yaml", "r") as f:
    context = f.read().split("---")
    data = yaml.safe_load(context[1])

from pprint import pprint

pprint(data)
