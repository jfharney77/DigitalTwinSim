"""FastAPI app: serves the Pro Max Plus inference-path map, the inference
trace, catalog, and use cases. All content is static data + a pure engine —
no state."""

from __future__ import annotations

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import CatalogCategory, DeviceAnatomy, InferenceResponse, UseCase
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="Dell Pro Max Plus Inside",
    frontend_port=5186,
)


@app.get("/api/anatomy", response_model=DeviceAnatomy)
def get_anatomy(level: int = Level) -> DeviceAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/inference", response_model=InferenceResponse)
def get_inference(level: int = Level) -> InferenceResponse:
    return leveled(InferenceResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)


@app.get("/api/tour", response_model=TourResponse)
def get_tour(level: int = Level) -> TourResponse:
    """The narrated tour: beats, camera boxes, layers and trace cursors."""
    return leveled(TOUR_RESPONSE, level)
