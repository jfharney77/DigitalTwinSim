"""The model base every component shares.

Every twin's ``models.py`` opened with the same four lines: a pydantic base
carrying ``alias_generator=to_camel`` so Python stays snake_case and the wire
stays camelCase, which is what the React frontends consume directly. Those
four lines were re-typed once per component, which meant the cross-cutting
gotcha below had to be re-learned once per component too.

**The gotcha, in one place at last.** ``to_camel`` camelizes on word
boundaries, so a field whose name embeds a number or an acronym can produce a
key the frontend does not expect: ``cores_per_sm`` becomes ``coresPerSm``, not
the ``coresPerSM`` the GPU twin's ``types.ts`` declares. Fields like that need
an explicit ``Field(alias=...)``; ``camel`` below is the helper that spells
that out at the call site.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

__all__ = ["CamelModel", "camel", "to_camel"]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


def camel(alias: str, **kwargs: Any) -> Any:
    """A field with an explicit wire name.

    Use it wherever ``to_camel`` would guess wrong — embedded numbers and
    acronyms are the usual culprits::

        cores_per_sm: Grid = camel("coresPerSM")

    Verify the key against the component's ``frontend/src/types.ts`` by hand;
    nothing else will.
    """
    return Field(alias=alias, **kwargs)
