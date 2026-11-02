# formats/

One JSON file per show format (`<name>.json`), with only the keys that differ from the defaults in
`tt_shorts/formats.py`. A file overrides a built-in format of the same name. See the `veasy:formats` skill
(`video/skills/`) and `python -m tt_shorts.engine options`.
