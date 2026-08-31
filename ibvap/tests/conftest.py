import sys
from pathlib import Path

# Add root directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

parent_dir = root_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Alias 'src' to 'ai.tracking' or root modules for legacy test compatibility
try:
    import ai.tracking.association as assoc_mod
    import ai.tracking.events as events_mod
    import ai.tracking.pipeline as pipe_mod
    import types

    src_module = types.ModuleType("src")
    src_module.association = assoc_mod
    src_module.events = events_mod
    src_module.pipeline = pipe_mod
    sys.modules["src"] = src_module
    sys.modules["src.association"] = assoc_mod
    sys.modules["src.association.person_vehicle"] = sys.modules.get("ai.tracking.association.person_vehicle")
    sys.modules["src.events"] = events_mod
    sys.modules["src.events.payload"] = sys.modules.get("ai.tracking.events.payload")
    sys.modules["src.events.publisher"] = sys.modules.get("ai.tracking.events.publisher")
    sys.modules["src.events.severity"] = sys.modules.get("ai.tracking.events.severity")
    sys.modules["src.pipeline"] = pipe_mod
except Exception:
    pass
