from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------------------------------------------------------------- reference

class DistrictOut(BaseModel):
    id: int
    key: str = Field(validation_alias="name")          # frontend calls it `key`
    landmark: str | None = Field(default=None, validation_alias="landmark_name")
    centerLat: float | None = Field(default=None, validation_alias="center_lat")
    centerLng: float | None = Field(default=None, validation_alias="center_lng")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class AccommodationTypeOut(BaseModel):
    code: str
    key: str = Field(validation_alias="name_th")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


AMENITY_CATEGORIES = [
    {"key": "room", "label": "ภายในห้อง"},
    {"key": "property", "label": "ภายในที่พัก"},
    {"key": "service", "label": "บริการ"},
    {"key": "parking", "label": "ที่จอดรถและการเดินทาง"},
    {"key": "accessibility", "label": "การรองรับพิเศษ"},
    {"key": "other", "label": "อื่นๆ"},
]
VALID_AMENITY_CATEGORIES = {c["key"] for c in AMENITY_CATEGORIES}


class AmenityOut(BaseModel):
    key: str = Field(validation_alias="code")
    label: str = Field(validation_alias="label_th")
    category: str | None = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class AdminAmenityOut(BaseModel):
    id: int
    key: str = Field(validation_alias="code")
    label: str = Field(validation_alias="label_th")
    category: str | None = None
    accommodationCount: int = 0

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class AmenityCreate(BaseModel):
    code: str
    label_th: str
    category: str | None = None
    icon_key: str | None = None


class AmenityUpdate(BaseModel):
    label_th: str | None = None
    category: str | None = None
    icon_key: str | None = None


# ------------------------------------------------------------ accommodation

class MatchReasonOut(BaseModel):
    """One itemized, typed reason a result matched the current search query
    — see app/match_reasons.py. Never a generic "ตรงกับคำค้นของคุณ" string;
    always backed by real data (a real POI+distance, a real facility on the
    accommodation, a real price, ...)."""

    type: str  # poi_match | poi_match_more | poi_current_location | type_match | price_match |
               # guest_count_match | facility_match | view_match | view_no_data |
               # atmosphere_match | atmosphere_no_data | special_condition_match
    message: str


class MatchedPoiOut(BaseModel):
    """One real, distance-verified nearby place behind a poi_match reason —
    lets the detail page list every matched place (not just the 3 shown on
    the card) with a real "เปิดเส้นทาง" link (spec §3/§13)."""

    poiId: int
    name: str
    category: str
    distanceKm: float
    isRoad: bool
    mapUrl: str | None = None


class AccommodationOut(BaseModel):
    """Shaped to match src/data/mockHotels.js exactly, so the Vue components
    (HotelCard.vue, StayCard.vue, etc.) need zero changes when wired to this API."""

    id: int
    name: str
    district: str            # district name, not id
    type: str                # type name_th, not id/code
    typeCode: str            # type code, e.g. 'hotel' | 'homestay' — drives per-category UI
    price: float
    rating: float
    reviews: int
    distanceKm: float | None
    landmark: str | None
    amenities: list[str]     # amenity codes
    tags: list[str]
    reason: str | None
    img: str
    fav: bool = False
    # optional, request-scoped annotations a homepage section adds on top of
    # the same card shape — never persisted, always computed per-viewer from
    # real data (see crud.py's home-section builders). None everywhere else.
    matchLevel: str | None = None        # "ตรงกับความต้องการมาก" | "...ต้องการ" | "...บางส่วน"
    matchReason: str | None = None       # why this card matched the current search/preferences
    matchReasons: list[MatchReasonOut] = []  # structured, itemized version — see app/match_reasons.py
    matchedCriteria: list[str] = []      # which requested criteria this card actually satisfies
    unmatchedCriteria: list[str] = []    # requested criteria the data couldn't confirm (drives "ตรงบางส่วน")
    matchedPois: list[MatchedPoiOut] = []  # every real nearby place behind a poi_match reason (not capped to 3)
    rank: int | None = None              # 1-based position within "ที่พักยอดนิยม"
    statLabel: str | None = None         # short real-stat line, e.g. "ถูกบันทึก 24 ครั้ง"
    distanceFromUserKm: float | None = None  # straight-line distance from the visitor's real geolocation coords — only set by /api/search/nearby
    googleMapsUrl: str | None = None     # real stored link, or built from the accommodation's own real coordinates — never the visitor's

    model_config = ConfigDict(from_attributes=True)


class ImageOut(BaseModel):
    url: str
    caption: str | None = None
    sourceNote: str | None = None
    isCover: bool = False


# --------------------------------------------------------- image management
# Two strictly separate galleries: AccommodationImage (accommodation_id) and
# RoomTypeImage (room_type_id) — never mixed, never fetched through one API.

IMAGE_STATUSES = {"published", "hidden", "pending"}

ACCOMMODATION_IMAGE_CATEGORIES = [
    ("exterior", "รูปด้านหน้าที่พัก"), ("building", "อาคาร"), ("entrance", "ทางเข้า"),
    ("lobby", "ล็อบบี้"), ("reception", "แผนกต้อนรับ"), ("common_area", "พื้นที่ส่วนกลาง"),
    ("pool", "สระว่ายน้ำ"), ("restaurant", "ร้านอาหาร"), ("dining", "ห้องอาหาร"),
    ("gym", "ฟิตเนส"), ("parking", "ที่จอดรถ"), ("garden", "สวน"),
    ("surroundings", "บริเวณโดยรอบ"), ("view", "วิวจากที่พัก"),
    ("atmosphere", "บรรยากาศภายนอก"), ("other", "อื่น ๆ"),
]
ROOM_IMAGE_CATEGORIES = [
    ("overview", "ภาพรวมห้อง"), ("bedroom", "ห้องนอน"), ("bed", "เตียง"),
    ("bathroom", "ห้องน้ำ"), ("bathtub", "อ่างอาบน้ำ"), ("balcony", "ระเบียง"),
    ("room_view", "วิวจากห้อง"), ("living_area", "พื้นที่นั่งเล่น"), ("desk", "โต๊ะทำงาน"),
    ("kitchen", "ห้องครัว"), ("closet", "ตู้เสื้อผ้า"), ("amenities", "สิ่งอำนวยความสะดวกภายในห้อง"),
    ("room_entrance", "ทางเข้าและบริเวณหน้าห้อง"), ("other", "อื่น ๆ"),
]
ACCOMMODATION_IMAGE_CATEGORY_CODES = {c for c, _ in ACCOMMODATION_IMAGE_CATEGORIES}
ROOM_IMAGE_CATEGORY_CODES = {c for c, _ in ROOM_IMAGE_CATEGORIES}


class ImageCategoryOut(BaseModel):
    key: str
    label: str


class ImageCategoriesOut(BaseModel):
    accommodation: list[ImageCategoryOut]
    roomType: list[ImageCategoryOut]


class AccommodationImageOut(BaseModel):
    id: int
    accommodationId: int = Field(validation_alias="accommodation_id")
    url: str = Field(validation_alias="image_url")
    thumbnailUrl: str | None = Field(default=None, validation_alias="thumbnail_url")
    category: str | None = Field(default=None, validation_alias="image_category")
    caption: str | None = None
    altText: str | None = Field(default=None, validation_alias="alt_text")
    sourceName: str | None = Field(default=None, validation_alias="source_name")
    sourceUrl: str | None = Field(default=None, validation_alias="source_url")
    isCover: bool = Field(validation_alias="is_cover")
    displayOrder: int = Field(validation_alias="sort_order")
    status: str
    uploadedBy: int | None = Field(default=None, validation_alias="uploaded_by")
    createdAt: datetime = Field(validation_alias="created_at")
    updatedAt: datetime = Field(validation_alias="updated_at")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class RoomTypeImageOut(BaseModel):
    id: int
    roomTypeId: int = Field(validation_alias="room_type_id")
    url: str = Field(validation_alias="image_url")
    thumbnailUrl: str | None = Field(default=None, validation_alias="thumbnail_url")
    category: str | None = Field(default=None, validation_alias="image_category")
    caption: str | None = None
    altText: str | None = Field(default=None, validation_alias="alt_text")
    sourceName: str | None = Field(default=None, validation_alias="source_name")
    sourceUrl: str | None = Field(default=None, validation_alias="source_url")
    isCover: bool = Field(validation_alias="is_cover")
    displayOrder: int = Field(validation_alias="sort_order")
    status: str
    uploadedBy: int | None = Field(default=None, validation_alias="uploaded_by")
    createdAt: datetime = Field(validation_alias="created_at")
    updatedAt: datetime = Field(validation_alias="updated_at")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ImageMetaPatch(BaseModel):
    category: str | None = None
    caption: str | None = None
    altText: str | None = None
    sourceName: str | None = None
    sourceUrl: str | None = None
    status: str | None = None


class ImageReorderIn(BaseModel):
    orderedIds: list[int]


class RoomTypeOut(BaseModel):
    id: int
    name: str
    price: float
    maxOccupancy: int | None = None
    standardOccupancy: int | None = None
    bedType: str | None = None
    view: str | None = None                 # garden|river|city|mountain|pool|none
    roomSizeSqm: float | None = None
    breakfastIncluded: bool = False
    extraBedAvailable: bool = False
    extraBedPrice: float | None = None
    extraBedMax: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    unitsAvailable: int | None = None
    childrenAllowed: bool | None = None
    smokingAllowed: bool | None = None
    petsAllowed: bool | None = None
    description: str | None = None
    roomAmenities: list[str] = []           # in-room amenity codes
    images: list[ImageOut] = []
    isVisible: bool = True


class RoomTypeCreate(BaseModel):
    name: str
    price_per_night: float
    max_occupancy: int | None = None
    standard_occupancy: int | None = None
    bed_type: str | None = None
    view_type: str | None = None
    room_size_sqm: float | None = None
    breakfast_included: bool = False
    extra_bed_available: bool = False
    extra_bed_price: float | None = None
    extra_bed_max: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    units_available: int | None = None
    children_allowed: bool | None = None
    smoking_allowed: bool | None = None
    pets_allowed: bool | None = None
    description: str | None = None
    room_amenities: list[str] = []
    # images are managed via /api/admin/room-types/{id}/images, not this form
    is_visible: bool = True
    sort_order: int = 0


class RoomTypeUpdate(BaseModel):
    name: str | None = None
    price_per_night: float | None = None
    max_occupancy: int | None = None
    standard_occupancy: int | None = None
    bed_type: str | None = None
    view_type: str | None = None
    room_size_sqm: float | None = None
    breakfast_included: bool | None = None
    extra_bed_available: bool | None = None
    extra_bed_price: float | None = None
    extra_bed_max: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    units_available: int | None = None
    children_allowed: bool | None = None
    smoking_allowed: bool | None = None
    pets_allowed: bool | None = None
    description: str | None = None
    room_amenities: list[str] | None = None
    is_visible: bool | None = None
    sort_order: int | None = None


class CategoryRatingsOut(BaseModel):
    """Only meaningful once review_count > 0 — the frontend hides this
    section entirely when there are no real reviews, rather than showing
    a row of fabricated-looking 0.0 bars."""

    cleanliness: float
    location: float
    service: float
    value: float


class PoliciesOut(BaseModel):
    checkinTime: str | None
    checkoutTime: str | None
    cancellationPolicy: str | None
    minAge: int | None
    smokingAllowed: bool | None
    depositRequired: bool
    depositNote: str | None
    depositAmount: float | None
    depositPercent: int | None
    advanceBookingRequired: bool
    advanceBookingDays: int | None
    priceConditions: str | None
    paymentMethods: list[str]


class ContactOut(BaseModel):
    phone: str | None
    line: str | None
    facebook: str | None
    instagram: str | None
    website: str | None


class AccommodationDetailOut(AccommodationOut):
    """Extends AccommodationOut with fields only the detail page needs —
    full description, contact/location info, every photo (not just the
    cover), room types, policies, and category rating breakdown.
    Used only by GET /api/accommodations/{id}."""

    description: str | None
    address: str | None
    phone: str | None
    latitude: float | None
    longitude: float | None
    googleMapsUrl: str | None
    images: list[ImageOut]
    roomTypes: list[RoomTypeOut]
    contact: ContactOut
    policies: PoliciesOut
    categoryRatings: CategoryRatingsOut
    # admin/editorial fields — meaningless-but-harmless for the public page,
    # which only ever receives status='published' rows anyway
    status: str
    lastVerifiedAt: date | None = None
    sourceNote: str | None = None
    isFeatured: bool = False


class AccommodationListOut(BaseModel):
    items: list[AccommodationOut]
    total: int
    page: int
    pageSize: int


class AdminAccommodationOut(AccommodationOut):
    """List row for the admin accommodations table — adds the workflow
    status and data-quality fields the public AccommodationOut doesn't need."""

    status: str
    lastVerifiedAt: date | None = None
    updatedAt: datetime
    isFeatured: bool = False


class AdminAccommodationListOut(BaseModel):
    items: list[AdminAccommodationOut]
    total: int
    page: int
    pageSize: int


class AdminDistrictTypeRow(BaseModel):
    district: str
    counts: dict[str, int]   # {'hotel': 5, 'resort': 2, 'homestay': 1}
    total: int


class AdminSummaryOut(BaseModel):
    """District x type breakdown for the admin accommodations page — every
    status counted, so it doubles as a data-quality check (a district/type
    combo stuck at 0 is easy to spot)."""

    typeCodes: list[str]
    typeLabels: dict[str, str]
    rows: list[AdminDistrictTypeRow]
    totals: dict[str, int]
    grandTotal: int


PLACE_CATEGORIES = [
    {"key": "temple", "label": "วัด/ศาสนสถาน"},
    {"key": "attraction", "label": "สถานที่ท่องเที่ยว"},
    {"key": "station", "label": "สถานีขนส่ง/ท่ารถ"},
    {"key": "mall", "label": "ห้างสรรพสินค้า"},
    {"key": "hospital", "label": "โรงพยาบาล"},
    {"key": "market", "label": "ตลาด"},
    {"key": "convenience", "label": "ร้านสะดวกซื้อ"},
    {"key": "restaurant", "label": "ร้านอาหาร"},
    {"key": "museum", "label": "พิพิธภัณฑ์"},
    {"key": "airport", "label": "สนามบิน"},
    {"key": "nightlife", "label": "สถานบันเทิง"},
    {"key": "university", "label": "มหาวิทยาลัย"},
]
VALID_PLACE_CATEGORIES = {c["key"] for c in PLACE_CATEGORIES}


class PlaceOut(BaseModel):
    name: str
    category: str
    distanceKm: float


class AdminPlaceOut(BaseModel):
    id: int
    name: str
    category: str
    latitude: float
    longitude: float
    address: str | None = None
    isPopular: bool = False
    sourceNote: str | None = None
    districtName: str | None = None


class PlaceCreate(BaseModel):
    name: str
    category: str
    latitude: float
    longitude: float
    address: str | None = None
    is_popular: bool = False
    source_note: str | None = None
    district_name: str | None = None


class PlaceUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    is_popular: bool | None = None
    source_note: str | None = None
    district_name: str | None = None


class AccommodationPlaceOut(BaseModel):
    """A curated distance link between one accommodation and one place —
    what the admin form manages; the public site reads this via
    crud.nearby_places instead of this endpoint."""
    id: int
    placeId: int
    placeName: str
    placeCategory: str
    placeIsPopular: bool = False
    distanceKm: float | None = None
    travelTimeMinutes: int | None = None
    travelMethod: str | None = None
    note: str | None = None
    routeUrl: str | None = None
    verifiedAt: date | None = None


class AccommodationPlaceCreate(BaseModel):
    place_id: int
    distance_km: float | None = None
    travel_time_minutes: int | None = None
    travel_method: str | None = None
    note: str | None = None
    route_url: str | None = None
    verified_at: date | None = None


class AccommodationPlaceUpdate(BaseModel):
    distance_km: float | None = None
    travel_time_minutes: int | None = None
    travel_method: str | None = None
    note: str | None = None
    route_url: str | None = None
    verified_at: date | None = None


class AdminNearbyPlaceOut(BaseModel):
    """Every place within radius of an accommodation — curated (has a real
    AccommodationPlace row, editable) or a live haversine estimate (not yet
    curated) — for the admin's browse-and-confirm nearby-places view. Mirrors
    what the public nearby-places modal shows, plus the ids needed to edit."""
    placeId: int
    name: str
    category: str
    distanceKm: float
    isPopular: bool = False
    isCurated: bool = False
    linkId: int | None = None


class NearbyOut(BaseModel):
    """Points of interest around one accommodation, distances computed live
    from the accommodation's coordinates (see crud.nearby_places)."""

    popular: list[PlaceOut]   # ที่เที่ยวยอดนิยม
    nearest: list[PlaceOut]   # สถานที่ใกล้ที่สุด (สั้น ๆ สำหรับการ์ด)
    all: list[PlaceOut]       # ทั้งหมดในรัศมี สำหรับ modal


class DistrictCountsOut(BaseModel):
    counts: dict[str, int]


# ------------------------------------------------------------------- admin

class AccommodationCreate(BaseModel):
    name: str
    type_code: str
    district_name: str
    description: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    google_maps_url: str | None = None
    price_per_night: float
    landmark_distance_km: float | None = None
    phone: str | None = None
    contact_line: str | None = None
    contact_facebook: str | None = None
    contact_instagram: str | None = None
    website_url: str | None = None
    # policies
    checkin_time: str | None = None
    checkout_time: str | None = None
    cancellation_policy: str | None = None
    min_age: int | None = None
    smoking_allowed: bool | None = None
    deposit_required: bool = False
    deposit_note: str | None = None
    payment_methods: list[str] = []
    # pricing conditions
    deposit_amount: float | None = None
    deposit_percent: int | None = None
    advance_booking_required: bool = False
    advance_booking_days: int | None = None
    price_conditions: str | None = None
    recommended_reason: str | None = None
    tags: list[str] = []
    amenity_codes: list[str] = []
    # images are managed via /api/admin/accommodations/{id}/images, not this form
    # editorial — new listings start as a draft until an admin publishes them
    status: str = "draft"
    last_verified_at: date | None = None
    source_note: str | None = None
    is_featured: bool = False


class AccommodationUpdate(BaseModel):
    name: str | None = None
    type_code: str | None = None
    district_name: str | None = None
    description: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    google_maps_url: str | None = None
    price_per_night: float | None = None
    landmark_distance_km: float | None = None
    phone: str | None = None
    contact_line: str | None = None
    contact_facebook: str | None = None
    contact_instagram: str | None = None
    website_url: str | None = None
    # policies
    checkin_time: str | None = None
    checkout_time: str | None = None
    cancellation_policy: str | None = None
    min_age: int | None = None
    smoking_allowed: bool | None = None
    deposit_required: bool | None = None
    deposit_note: str | None = None
    payment_methods: list[str] | None = None
    # pricing conditions
    deposit_amount: float | None = None
    deposit_percent: int | None = None
    advance_booking_required: bool | None = None
    advance_booking_days: int | None = None
    price_conditions: str | None = None
    recommended_reason: str | None = None
    tags: list[str] | None = None
    amenity_codes: list[str] | None = None
    status: str | None = None
    last_verified_at: date | None = None
    source_note: str | None = None
    is_featured: bool | None = None


# -------------------------------------------------------------------- auth

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AdminMemberOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    isActive: bool
    createdAt: datetime
    favoriteCount: int = 0


class AdminMemberListOut(BaseModel):
    items: list[AdminMemberOut]
    total: int
    page: int
    pageSize: int


class MemberStatusUpdate(BaseModel):
    is_active: bool


class DataQualityOut(BaseModel):
    totalPublished: int
    missingVerification: int
    staleVerification: int  # last_verified_at older than 90 days


class FavoritedAccommodationOut(BaseModel):
    id: int
    name: str
    favoriteCount: int


class SearchTermStatOut(BaseModel):
    term: str
    count: int


class AdminStatsOut(BaseModel):
    totalMembers: int
    activeMembers: int
    suspendedMembers: int
    dataQuality: DataQualityOut
    topFavorited: list[FavoritedAccommodationOut]
    topSearchTerms: list[SearchTermStatOut]
    noResultSearchTerms: list[SearchTermStatOut]
    totalSearches: int
    comparisonFeatureBuilt: bool = False  # comparison (spec item 2) isn't implemented yet — no usage stats to show


# ------------------------------------------------------------------ search

class SearchRequest(BaseModel):
    query: str
    type: str | None = None
    district: list[str] = []
    price_min: float | None = None
    price_max: float | None = None
    rating_min: float | None = None
    amenities: list[str] = []
    distance_max_km: float | None = None
    guest_count: int | None = None
    smoking: bool | None = None
    extra_bed: bool | None = None
    raw: bool = False  # skip typo/informal-term correction — "ใช้ข้อความเดิม" (spec §10)
    page: int = 1
    page_size: int = 6


class TermCorrectionOut(BaseModel):
    original: str
    canonical: str


class SearchMeta(BaseModel):
    priceCeiling: float | None
    terms: list[str]
    originalQuery: str | None = None
    normalizedQuery: str | None = None
    interpretedAs: str | None = None       # human-readable Thai recap of what was understood
    detectedFilters: list[str] = []        # for the results-page condition-chip bar
    confidence: float | None = None        # 1.0 = exact dictionary match, lower = fuzzy-fallback correction
    corrections: list[TermCorrectionOut] = []
    notFoundMessage: str | None = None     # set when a named POI/category has no resolvable data (spec §15)
    notFoundOptions: list[str] = []


class SearchResponse(BaseModel):
    items: list[AccommodationOut]
    total: int
    page: int
    pageSize: int
    meta: SearchMeta
    otherSuggestions: list[AccommodationOut] = []  # "ที่พักอื่นที่อาจสนใจ" — only populated alongside notFoundMessage, never claimed as a match


# ------------------------------------------------------------- suggestions

class QuerySuggestionOut(BaseModel):
    text: str


class PoiSuggestionOut(BaseModel):
    name: str
    category: str


class AccommodationSuggestionOut(BaseModel):
    id: int
    name: str
    type: str
    district: str
    matchedPoiName: str | None = None
    distanceKm: float | None = None


class SearchSuggestionsOut(BaseModel):
    originalQuery: str
    normalizedQuery: str
    interpretedAs: str | None = None
    querySuggestions: list[str] = []
    poiSuggestions: list[PoiSuggestionOut] = []
    accommodationSuggestions: list[AccommodationSuggestionOut] = []


# ------------------------------------------------------------- nearby search

class NearbySearchRequest(BaseModel):
    latitude: float
    longitude: float
    query: str = ""
    accommodation_type: str | None = None   # explicit UI type filter — wins over anything detected in `query`
    radius_km: float = 10
    price_min: float | None = None
    price_max: float | None = None
    rating_min: float | None = None
    facilities: list[str] = []              # explicit UI amenity-code filter
    district: list[str] = []
    guest_count: int | None = None
    sort_by: str = "relevance"              # 'relevance' | 'distance' | 'price-asc'
    raw: bool = False  # skip typo/informal-term correction — "ใช้ข้อความเดิม" (spec §10)
    page: int = 1
    page_size: int = 12


class DetectedIntentOut(BaseModel):
    useCurrentLocation: bool
    accommodationType: str | None
    facilities: list[str]
    priceMax: float | None


class NearbySearchResponse(BaseModel):
    title: str
    subtitle: str
    query: str
    detectedIntent: DetectedIntentOut
    radiusKm: float               # radius actually used, after any auto-expansion
    requestedRadiusKm: float      # radius the caller asked for
    radiusExpanded: bool
    radiusExpandedMessage: str | None
    accommodationType: str | None
    facilities: list[str]
    priceMax: float | None
    district: list[str]
    sortBy: str
    total: int
    resultCount: int
    page: int
    pageSize: int
    items: list[AccommodationOut]
    normalizedQuery: str | None = None
    interpretedAs: str | None = None
    detectedFilters: list[str] = []
    confidence: float | None = None
    corrections: list[TermCorrectionOut] = []
    notFoundMessage: str | None = None
    notFoundOptions: list[str] = []
    otherSuggestions: list[AccommodationOut] = []


# ----------------------------------------------------------------- reviews

class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    cleanliness_rating: int | None = Field(default=None, ge=1, le=5)
    location_rating: int | None = Field(default=None, ge=1, le=5)
    service_rating: int | None = Field(default=None, ge=1, le=5)
    value_rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None


class ReviewOut(BaseModel):
    id: int
    rating: int
    cleanlinessRating: int | None = None
    locationRating: int | None = None
    serviceRating: int | None = None
    valueRating: int | None = None
    comment: str | None
    createdAt: datetime
    userName: str


class ReviewListOut(BaseModel):
    items: list[ReviewOut]
    total: int
    page: int
    pageSize: int


# ------------------------------------------------------------------- home

ATMOSPHERE_OPTIONS = [
    {"key": "quiet", "label": "เงียบสงบ"},
    {"key": "nature", "label": "ใกล้ธรรมชาติ"},
    {"key": "city", "label": "ใจกลางเมือง"},
    {"key": "family", "label": "เหมาะสำหรับครอบครัว"},
]
VALID_ATMOSPHERE_CODES = {o["key"] for o in ATMOSPHERE_OPTIONS}

EVENT_TYPES = {"view", "favorite", "compare", "contact_click", "direction_click"}


class EventCreate(BaseModel):
    event_type: str


class UserPreferenceIn(BaseModel):
    type_codes: list[str] = []
    district_names: list[str] = []
    budget_min: float | None = None
    budget_max: float | None = None
    guest_count: int | None = None
    amenity_codes: list[str] = []
    atmosphere_codes: list[str] = []
    near_place_categories: list[str] = []


class UserPreferenceOut(UserPreferenceIn):
    updatedAt: datetime


class PersonalizationSettingsOut(BaseModel):
    allowPersonalization: bool


class PersonalizationSettingsIn(BaseModel):
    allow_personalization: bool


class SearchHistorySettingOut(BaseModel):
    saveSearchHistory: bool


class SearchHistorySettingIn(BaseModel):
    save_search_history: bool


class OnboardingOptionsOut(BaseModel):
    title: str
    subtitle: str
    typeOptions: list[AccommodationTypeOut]
    districtOptions: list[DistrictOut]
    amenityOptions: list[AmenityOut]
    atmosphereOptions: list[dict]
    placeCategoryOptions: list[dict]


class HomeSectionOut(BaseModel):
    key: str
    title: str
    subtitle: str
    badge: str | None = None
    items: list[AccommodationOut]


class HomeOut(BaseModel):
    matchSection: HomeSectionOut | None = None
    personalSection: HomeSectionOut | None = None
    onboarding: OnboardingOptionsOut | None = None
    featuredSection: HomeSectionOut | None = None
    popularSection: HomeSectionOut | None = None
    recentlyViewedSection: HomeSectionOut | None = None
    # only set when `q` was real query text — lets the home page hero search
    # carry the same real, structured search context (spec §14) into the
    # detail page as a search run from /hotels does.
    searchMeta: SearchMeta | None = None
