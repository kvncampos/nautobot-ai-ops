"""Custom JSON encoders for serialization."""

import json
from decimal import Decimal
from typing import Any


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal objects."""

    def default(self, obj: Any) -> Any:
        """Convert Decimal to float for JSON serialization."""
        if isinstance(obj, Decimal):
            return float(obj)  # or str(obj)
        return super().default(obj)
