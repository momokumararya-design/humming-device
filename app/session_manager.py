import json
from pathlib import Path
from app.config import new_session_dir

class SessionManager:
    def create(self):
        d = new_session_dir()
        self.dir = d
        return d
    def save_json(self, name, data):
        (self.dir/name).write_text(json.dumps(data, indent=2))
    def path(self, name):
        return self.dir/name
