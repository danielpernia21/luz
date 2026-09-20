import json
import pathlib

import pytest

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def prices() -> dict[int, float]:
    raw = json.loads((FIXTURES / "prices_sample.json").read_text(encoding="utf-8"))
    return {int(h): v for h, v in raw.items()}
