import os
import shutil

# Runs before app modules are imported, so the engine has not opened the file yet.
_here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _db in ("mon_comptable.db",):
    _path = os.path.join(_here, _db)
    if os.path.exists(_path):
        os.remove(_path)
_docs = os.path.join(_here, "data", "documents")
if os.path.isdir(_docs):
    shutil.rmtree(_docs, ignore_errors=True)
