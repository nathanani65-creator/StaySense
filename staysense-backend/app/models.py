from datetime import date, datetime

from sqlalchemy import (
    String, Text, Integer, Numeric, Boolean, ForeignKey, TIMESTAMP, Date,
    UniqueConstraint, JSON, Enum, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    province: Mapped[str] = mapped_column(String(100), default="พิษณุโลก")
    landmark_name: Mapped[str | None] = mapped_column(String(150))
    center_lat: Mapped[float | None] = mapped_column(Numeric(10, 7))
    center_lng: Mapped[float | None] = mapped_column(Numeric(10, 7))

    accommodations: Mapped[list["Accommodation"]] = relationship(back_populates="district")


class AccommodationType(Base):
    __tablename__ = "accommodation_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)   # 'hotel' | 'resort' | ...
    name_th: Mapped[str] = mapped_column(String(100))            # 'โรงแรม' | 'รีสอร์ต' | ...
    icon_key: Mapped[str | None] = mapped_column(String(50))

    accommodations: Mapped[list["Accommodation"]] = relationship(back_populates="type")


class Amenity(Base):
    __tablename__ = "amenities"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)   # 'wifi' | 'parking' | ...
    label_th: Mapped[str] = mapped_column(String(100))
    icon_key: Mapped[str | None] = mapped_column(String(50))
    category: Mapped[str | None] = mapped_column(String(30))     # 'room'|'property'|'service'|'parking'|'accessibility'|'other'


class AccommodationAmenity(Base):
    __tablename__ = "accommodation_amenities"

    accommodation_id: Mapped[int] = mapped_column(ForeignKey("accommodations.id", ondelete="CASCADE"), primary_key=True)
    amenity_id: Mapped[int] = mapped_column(ForeignKey("amenities.id", ondelete="CASCADE"), primary_key=True)


class Accommodation(Base):
    __tablename__ = "accommodations"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_code: Mapped[str | None] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    type_id: Mapped[int] = mapped_column(ForeignKey("accommodation_types.id"))
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"))
    description: Mapped[str | None] = mapped_column(Text)          # used to build the embedding
    address: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    price_per_night: Mapped[float] = mapped_column(Numeric(10, 2))
    landmark_distance_km: Mapped[float | None] = mapped_column(Numeric(5, 2))
    phone: Mapped[str | None] = mapped_column(String(20))
    # contact channels (schema_addendum_5.sql)
    contact_line: Mapped[str | None] = mapped_column(String(120))
    contact_facebook: Mapped[str | None] = mapped_column(String(255))
    contact_instagram: Mapped[str | None] = mapped_column(String(120))
    website_url: Mapped[str | None] = mapped_column(String(255))
    google_maps_url: Mapped[str | None] = mapped_column(String(500))
    rating_avg: Mapped[float] = mapped_column(Numeric(2, 1), default=0)
    # per-category rating averages — always derived from real reviews via
    # the DB triggers in schema_addendum_3.sql, never hand-set. Read-only
    # from the application's point of view.
    rating_cleanliness: Mapped[float] = mapped_column(Numeric(2, 1), default=0)
    rating_location: Mapped[float] = mapped_column(Numeric(2, 1), default=0)
    rating_service: Mapped[float] = mapped_column(Numeric(2, 1), default=0)
    rating_value: Mapped[float] = mapped_column(Numeric(2, 1), default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    recommended_reason: Mapped[str | None] = mapped_column(String(255))
    # lightweight extension beyond the original schema: free-form display
    # tags shown as pills on the card (e.g. ["วิวแม่น้ำ", "เงียบสงบ"]).
    # Add with: ALTER TABLE accommodations ADD COLUMN tags_json JSON NULL;
    tags_json: Mapped[list | None] = mapped_column(JSON)
    # policies (schema_addendum_3.sql)
    checkin_time: Mapped[str | None] = mapped_column(String(20))
    checkout_time: Mapped[str | None] = mapped_column(String(20))
    cancellation_policy: Mapped[str | None] = mapped_column(Text)
    min_age: Mapped[int | None] = mapped_column(Integer)
    smoking_allowed: Mapped[bool | None] = mapped_column(Boolean)
    deposit_required: Mapped[bool] = mapped_column(Boolean, default=False)
    deposit_note: Mapped[str | None] = mapped_column(String(255))
    # pricing conditions (schema_addendum_5.sql)
    deposit_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    deposit_percent: Mapped[int | None] = mapped_column(Integer)
    advance_booking_required: Mapped[bool] = mapped_column(Boolean, default=False)
    advance_booking_days: Mapped[int | None] = mapped_column(Integer)
    price_conditions: Mapped[str | None] = mapped_column(Text)
    payment_methods_json: Mapped[list | None] = mapped_column(JSON)
    # editorial workflow (schema_addendum_9.sql) — replaces the old active/inactive
    # flag so admins can unpublish without deleting. Only 'published' rows are
    # ever shown to the public (see crud.base_accommodation_query).
    status: Mapped[str] = mapped_column(
        Enum("draft", "pending_review", "published", "closed"), default="draft"
    )
    # admin-curated pick for the homepage "ที่พักน่าสนใจ" section, used while
    # there isn't enough real accommodation_events data for a genuine
    # popularity ranking (schema_addendum_16.sql)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    # data-quality tracking for the admin (schema_addendum_9.sql)
    last_verified_at: Mapped[date | None] = mapped_column(Date)
    source_note: Mapped[str | None] = mapped_column(String(500))

    type: Mapped["AccommodationType"] = relationship(back_populates="accommodations")
    district: Mapped["District"] = relationship(back_populates="accommodations")
    images: Mapped[list["AccommodationImage"]] = relationship(back_populates="accommodation", cascade="all, delete-orphan")
    amenities: Mapped[list["Amenity"]] = relationship(secondary="accommodation_amenities")
    reviews: Mapped[list["Review"]] = relationship(back_populates="accommodation", cascade="all, delete-orphan")
    room_types: Mapped[list["RoomType"]] = relationship(back_populates="accommodation", cascade="all, delete-orphan", order_by="RoomType.sort_order")


class RoomType(Base):
    __tablename__ = "room_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_code: Mapped[str | None] = mapped_column(String(30), unique=True)
    accommodation_id: Mapped[int] = mapped_column(ForeignKey("accommodations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))                 # 'Standard' | 'Deluxe' | 'Family' | 'บ้านริมน้ำ' ...
    price_per_night: Mapped[float] = mapped_column(Numeric(10, 2))
    max_occupancy: Mapped[int | None] = mapped_column(Integer)      # จุได้สูงสุด (รวมเสริมเตียง / ทั้งหลัง)
    # จุปกติโดยไม่เสริมเตียง — โรงแรมมักเป็น 2, เสริมเตียงแล้วถึง max_occupancy
    standard_occupancy: Mapped[int | None] = mapped_column(Integer)
    bed_type: Mapped[str | None] = mapped_column(String(100))
    view_type: Mapped[str | None] = mapped_column(String(20))       # garden|river|city|mountain|pool|none
    room_size_sqm: Mapped[float | None] = mapped_column(Numeric(6, 1))
    breakfast_included: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_bed_available: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_bed_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    extra_bed_max: Mapped[int | None] = mapped_column(Integer)
    # โฮมสเตย์ / วิลล่า: อธิบายเป็น "หลัง"
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[int | None] = mapped_column(Integer)
    units_available: Mapped[int | None] = mapped_column(Integer)    # มีห้อง/หลังประเภทนี้กี่ยูนิต
    children_allowed: Mapped[bool | None] = mapped_column(Boolean)
    smoking_allowed: Mapped[bool | None] = mapped_column(Boolean)
    pets_allowed: Mapped[bool | None] = mapped_column(Boolean)
    description: Mapped[str | None] = mapped_column(Text)
    room_amenities_json: Mapped[list | None] = mapped_column(JSON)  # ['aircon','wifi','tv',...]
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)  # admin can hide without deleting

    accommodation: Mapped["Accommodation"] = relationship(back_populates="room_types")
    images: Mapped[list["RoomTypeImage"]] = relationship(
        back_populates="room_type", cascade="all, delete-orphan", order_by="RoomTypeImage.sort_order"
    )


class RoomTypeImage(Base):
    __tablename__ = "room_type_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id", ondelete="CASCADE"))
    image_url: Mapped[str] = mapped_column(String(1024))
    image_category: Mapped[str | None] = mapped_column(String(50))
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False)
    caption: Mapped[str | None] = mapped_column(String(255))
    alt_text: Mapped[str | None] = mapped_column(String(255))
    source_name: Mapped[str | None] = mapped_column(String(150))
    source_url: Mapped[str | None] = mapped_column(String(1024))
    source_note: Mapped[str | None] = mapped_column(String(255))  # legacy, kept for old rows
    status: Mapped[str] = mapped_column(Enum("published", "hidden", "pending"), default="published")
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    room_type: Mapped["RoomType"] = relationship(back_populates="images")


class AccommodationImage(Base):
    __tablename__ = "accommodation_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_code: Mapped[str | None] = mapped_column(String(30), unique=True)
    accommodation_id: Mapped[int] = mapped_column(ForeignKey("accommodations.id", ondelete="CASCADE"))
    image_url: Mapped[str] = mapped_column(String(1024))
    image_category: Mapped[str | None] = mapped_column(String(50))
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False)
    caption: Mapped[str | None] = mapped_column(String(255))
    alt_text: Mapped[str | None] = mapped_column(String(255))
    source_name: Mapped[str | None] = mapped_column(String(150))
    source_url: Mapped[str | None] = mapped_column(String(1024))
    source_note: Mapped[str | None] = mapped_column(String(255))  # legacy, kept for old rows
    status: Mapped[str] = mapped_column(Enum("published", "hidden", "pending"), default="published")
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    accommodation: Mapped["Accommodation"] = relationship(back_populates="images")


class ImageAuditLog(Base):
    __tablename__ = "image_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(30))       # create|update|cover|status|reorder|delete
    image_group: Mapped[str] = mapped_column(String(20))  # accommodation|room_type
    accommodation_id: Mapped[int | None] = mapped_column(Integer)
    room_type_id: Mapped[int | None] = mapped_column(Integer)
    image_id: Mapped[int] = mapped_column(Integer)
    old_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class Place(Base):
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_code: Mapped[str | None] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(30))
    latitude: Mapped[float] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float] = mapped_column(Numeric(10, 7))
    address: Mapped[str | None] = mapped_column(String(300))
    is_popular: Mapped[bool] = mapped_column(Boolean, default=False)
    source_note: Mapped[str | None] = mapped_column(String(255))
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    district: Mapped["District"] = relationship()


class AccommodationPlace(Base):
    """Curated accommodation<->place distance, used in place of the pure
    haversine straight-line estimate when a real, manually-verified figure
    (from the data-collection spreadsheet) is available."""

    __tablename__ = "accommodation_places"
    __table_args__ = (UniqueConstraint("accommodation_id", "place_id", name="uq_accommodation_place"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    external_code: Mapped[str | None] = mapped_column(String(30), unique=True)
    accommodation_id: Mapped[int] = mapped_column(ForeignKey("accommodations.id", ondelete="CASCADE"))
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"))
    distance_km: Mapped[float | None] = mapped_column(Numeric(6, 2))
    travel_time_minutes: Mapped[int | None] = mapped_column(Integer)
    travel_method: Mapped[str | None] = mapped_column(String(50))
    note: Mapped[str | None] = mapped_column(String(255))
    route_url: Mapped[str | None] = mapped_column(String(500))
    source_note: Mapped[str | None] = mapped_column(String(255))
    verified_at: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    accommodation: Mapped["Accommodation"] = relationship()
    place: Mapped["Place"] = relationship()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(Enum("user", "admin"), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # opt-out for using search history in recommendations (schema_addendum_16.sql)
    allow_personalization: Mapped[bool] = mapped_column(Boolean, default=True)
    # opt-out for writing to search_logs at all (schema_addendum_19.sql)
    save_search_history: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class SearchLog(Base):
    __tablename__ = "search_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    query_text: Mapped[str] = mapped_column(String(500))
    # what the query normalized to (typo/informal-term correction applied)
    # and what the parser understood from it — schema_addendum_19.sql
    normalized_query: Mapped[str | None] = mapped_column(String(500))
    detected_intent_json: Mapped[dict | None] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    extracted_price_max: Mapped[float | None] = mapped_column(Numeric(10, 2))
    extracted_district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id", ondelete="SET NULL"))
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    # nearby-search metadata (schema_addendum_17.sql) — deliberately no lat/lng column here
    accommodation_type: Mapped[str | None] = mapped_column(String(30))
    facilities_json: Mapped[list | None] = mapped_column(JSON)
    radius_km: Mapped[float | None] = mapped_column(Numeric(5, 2))
    sort_by: Mapped[str | None] = mapped_column(String(20))
    use_current_location: Mapped[bool] = mapped_column(Boolean, default=False)


class SearchTerm(Base):
    """Typo / abbreviation / informal-term dictionary that
    query_intent.normalize_query() uses to correct free-text search queries
    before parsing (schema_addendum_19.sql). Seeded via migration for now —
    no admin UI yet."""

    __tablename__ = "search_terms"

    id: Mapped[int] = mapped_column("search_term_id", primary_key=True)
    input_term: Mapped[str] = mapped_column(String(100), unique=True)
    canonical_term: Mapped[str] = mapped_column(String(150))
    term_type: Mapped[str] = mapped_column(
        Enum("accommodation_type", "poi_category", "poi_name", "facility", "district", "general")
    )
    reference_id: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0)
    status: Mapped[str] = mapped_column(Enum("active", "inactive"), default="active")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "accommodation_id", name="uq_fav_user_acc"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    accommodation_id: Mapped[int] = mapped_column(ForeignKey("accommodations.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_code: Mapped[str | None] = mapped_column(String(30), unique=True)
    accommodation_id: Mapped[int] = mapped_column(ForeignKey("accommodations.id", ondelete="CASCADE"))
    # NULL for a review imported from an external source (e.g. Agoda) that
    # isn't tied to a real registered StaySense member — guest_name carries
    # the real reviewer's name in that case instead of inventing an account.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    guest_name: Mapped[str | None] = mapped_column(String(150))
    rating: Mapped[int] = mapped_column(Integer)
    cleanliness_rating: Mapped[int | None] = mapped_column(Integer)
    location_rating: Mapped[int | None] = mapped_column(Integer)
    service_rating: Mapped[int | None] = mapped_column(Integer)
    value_rating: Mapped[int | None] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    accommodation: Mapped["Accommodation"] = relationship(back_populates="reviews")
    user: Mapped["User"] = relationship()


class AccommodationEvent(Base):
    """Real usage signal — a view, a favorite-add, a compare-add, a contact
    click, or a direction click — logged so 'ที่พักยอดนิยม' can be computed
    from actual behavior instead of being invented (schema_addendum_16.sql)."""

    __tablename__ = "accommodation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    accommodation_id: Mapped[int] = mapped_column(ForeignKey("accommodations.id", ondelete="CASCADE"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(
        Enum("view", "favorite", "compare", "contact_click", "direction_click")
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class UserPreference(Base):
    """What a member told the homepage's 'บอกความต้องการของคุณ' onboarding
    box — the direct input for personalized recommendations and their
    stated reasons (schema_addendum_16.sql)."""

    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    type_codes: Mapped[list | None] = mapped_column(JSON)
    district_names: Mapped[list | None] = mapped_column(JSON)
    budget_min: Mapped[float | None] = mapped_column(Numeric(10, 2))
    budget_max: Mapped[float | None] = mapped_column(Numeric(10, 2))
    guest_count: Mapped[int | None] = mapped_column(Integer)
    amenity_codes: Mapped[list | None] = mapped_column(JSON)
    atmosphere_codes: Mapped[list | None] = mapped_column(JSON)
    near_place_categories: Mapped[list | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
