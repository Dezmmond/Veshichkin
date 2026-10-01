"""Export the FastAPI contract without starting a server or connecting to the database."""

import json
from pathlib import Path

from veshichkin.main import app


def main() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    output = repository_root / "frontend" / "openapi.json"
    output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Exported OpenAPI to {output}")


if __name__ == "__main__":
    main()
