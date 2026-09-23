import logging
import mimetypes
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import SessionLocal
from .routers import (
    accommodations,
    admin,
    admin_accommodation_places,
    admin_amenities,
    admin_members,
    admin_places,
    admin_room_types,
    auth,
    districts,
    favorites,
    home,
    images,
    reference,
    reviews,
    search,
)
from .semantic import index as search_index

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("staysense")

settings = get_settings()

app = FastAPI(
    title="StaySense Phitsanulok API",
    description="Backend for the StaySense Phitsanulok accommodation search & semantic search demo.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accommodations.router)
app.include_router(districts.router)
app.include_router(reference.router)
app.include_router(search.router)
app.include_router(auth.router)
app.include_router(favorites.router)
app.include_router(reviews.router)
app.include_router(admin.router)
app.include_router(admin_room_types.router)
app.include_router(admin_amenities.router)
app.include_router(admin_places.router)
app.include_router(admin_accommodation_places.router)
app.include_router(admin_members.router)
app.include_router(home.router)
app.include_router(images.router)

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
# Windows' registry-backed mimetypes module often doesn't know .webp, which
# would make StaticFiles serve every uploaded image as text/plain — browsers
# refuse to render an <img> with that content-type regardless of its bytes.
mimetypes.add_type("image/webp", ".webp")
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.on_event("startup")
def on_startup():
    """Build the semantic search index once at boot. In production, also
    call POST /api/search/reindex after bulk data changes."""
    db = SessionLocal()
    try:
        count = search_index.build_index(db)
        logger.info("Semantic search index built with %d accommodations", count)
    except Exception:
        # Don't crash the whole API if the embedding model can't load
        # (e.g. no internet on first run to download it) — search will
        # just return empty results until /api/search/reindex succeeds.
        logger.exception("Failed to build semantic search index at startup")
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}
