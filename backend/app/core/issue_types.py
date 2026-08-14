import enum


class IssueCategory(str, enum.Enum):
    STREETLIGHT = "STREETLIGHT"
    POTHOLE = "POTHOLE"
    GARBAGE_OVERFLOW = "GARBAGE_OVERFLOW"
    WATER_LEAKAGE = "WATER_LEAKAGE"
    DAMAGED_PUBLIC_PROPERTY = "DAMAGED_PUBLIC_PROPERTY"
    ILLEGAL_DUMPING = "ILLEGAL_DUMPING"
    BROKEN_DRAINAGE = "BROKEN_DRAINAGE"


class IssueStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


CATEGORY_LABELS: dict[IssueCategory, str] = {
    IssueCategory.STREETLIGHT: "Streetlight",
    IssueCategory.POTHOLE: "Pothole",
    IssueCategory.GARBAGE_OVERFLOW: "Overflowing Garbage",
    IssueCategory.WATER_LEAKAGE: "Water Leakage",
    IssueCategory.DAMAGED_PUBLIC_PROPERTY: "Damaged Public Property",
    IssueCategory.ILLEGAL_DUMPING: "Illegal Dumping",
    IssueCategory.BROKEN_DRAINAGE: "Broken Drainage",
}

CATEGORY_RADIUS_METERS: dict[IssueCategory, float] = {
    IssueCategory.POTHOLE: 25,
    IssueCategory.STREETLIGHT: 30,
    IssueCategory.DAMAGED_PUBLIC_PROPERTY: 30,
    IssueCategory.GARBAGE_OVERFLOW: 50,
    IssueCategory.ILLEGAL_DUMPING: 60,
    IssueCategory.WATER_LEAKAGE: 80,
    IssueCategory.BROKEN_DRAINAGE: 80,
}

CATEGORY_WINDOW_DAYS: dict[IssueCategory, int] = {
    IssueCategory.GARBAGE_OVERFLOW: 3,
    IssueCategory.ILLEGAL_DUMPING: 7,
    IssueCategory.WATER_LEAKAGE: 10,
    IssueCategory.BROKEN_DRAINAGE: 30,
    IssueCategory.STREETLIGHT: 45,
    IssueCategory.POTHOLE: 60,
    IssueCategory.DAMAGED_PUBLIC_PROPERTY: 60,
}

SEVERITY_WEIGHTS: dict[IssueCategory, int] = {
    IssueCategory.WATER_LEAKAGE: 5,
    IssueCategory.BROKEN_DRAINAGE: 5,
    IssueCategory.POTHOLE: 4,
    IssueCategory.STREETLIGHT: 3,
    IssueCategory.DAMAGED_PUBLIC_PROPERTY: 3,
    IssueCategory.GARBAGE_OVERFLOW: 2,
    IssueCategory.ILLEGAL_DUMPING: 2,
}

# Service-level agreement: days a case may stay open before it escalates
# to higher authority. Urgent utilities get tight limits; structural work
# gets more room.
SLA_DAYS: dict[IssueCategory, int] = {
    IssueCategory.GARBAGE_OVERFLOW: 2,
    IssueCategory.WATER_LEAKAGE: 3,
    IssueCategory.ILLEGAL_DUMPING: 4,
    IssueCategory.BROKEN_DRAINAGE: 5,
    IssueCategory.POTHOLE: 7,
    IssueCategory.STREETLIGHT: 7,
    IssueCategory.DAMAGED_PUBLIC_PROPERTY: 10,
}

CLOSED_STATUSES: tuple[IssueStatus, ...] = (IssueStatus.RESOLVED, IssueStatus.REJECTED)

STATUS_FLOW: tuple[IssueStatus, ...] = (
    IssueStatus.SUBMITTED,
    IssueStatus.UNDER_REVIEW,
    IssueStatus.IN_PROGRESS,
    IssueStatus.RESOLVED,
)
