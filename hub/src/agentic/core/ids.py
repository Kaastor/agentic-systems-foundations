from __future__ import annotations

import uuid
from datetime import datetime


def new_run_id() -> str:
    """Create a human-inspectable run id.

    Example: ``run-20251121-153012-a1b2c3d4``
    """
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    rand = uuid.uuid4().hex[:8]
    return f"run-{ts}-{rand}"
