"""Root conftest: put the repo root on the path so ``twinkit`` imports.

The harder half of running 42 components in one interpreter lives in
``twinkit.testing.claim_backend`` and in the generated
``<component>/backend/conftest.py`` files that call it — every component's
backend package is called ``app``, so they take turns holding the name. See
``scripts/gen_root_pytest.py``.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_ROOT = str(pathlib.Path(__file__).resolve().parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from twinkit.testing import activate_backend_for  # noqa: E402  (path set up above)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    # Collection leaves ``app`` held by whichever backend was collected last;
    # hand it back to this test's backend before fixtures or the body run.
    activate_backend_for(item.path)
