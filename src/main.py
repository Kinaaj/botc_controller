import yaml

with open("config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# Seznam žárovek pro inicializaci controllerů
bulbs_config = config['network']['yeelights']