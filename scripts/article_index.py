"""Minimal front-matter reader used by the Patreon inventory."""
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def metadata(path):
    parts = path.read_text(encoding='utf-8-sig').split('+++', 2)
    if len(parts) != 3 or parts[0].strip():
        raise ValueError(f'Expected TOML front matter: {path}')
    return tomllib.loads(parts[1])
