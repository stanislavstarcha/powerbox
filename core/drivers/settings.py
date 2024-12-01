import ujson


class Settings:

    _filename = None
    _settings = None

    def __init__(self, filename="settings.json"):
        self._filename = filename
        self._read()

    def set(self, name, value):
        self._settings[name] = value
        self._write()

    def get(self, name):
        return self._settings.get(name)

    def _read(self):
        with open(self._filename, "r") as f:
            self._settings = ujson.load(f)

    def _write(self):
        with open(self._filename, "w+") as f:
            f.write(ujson.dumps(self._settings))
