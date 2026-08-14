export const CATEGORIES = [
  {
    value: "STREETLIGHT",
    label: "Streetlight",
    icon: "💡",
    hint: "Lamp not working, flickering, or damaged pole",
  },
  {
    value: "POTHOLE",
    label: "Pothole",
    icon: "🛣️",
    hint: "Damaged or broken road surface",
  },
  {
    value: "GARBAGE_OVERFLOW",
    label: "Overflowing Garbage",
    icon: "🗑️",
    hint: "Bin overflowing or waste not collected",
  },
  {
    value: "WATER_LEAKAGE",
    label: "Water Leakage",
    icon: "💧",
    hint: "Burst pipe, leaking main, or wasted water",
  },
  {
    value: "DAMAGED_PUBLIC_PROPERTY",
    label: "Damaged Public Property",
    icon: "🏗️",
    hint: "Broken bench, railing, sign, or shelter",
  },
  {
    value: "ILLEGAL_DUMPING",
    label: "Illegal Dumping",
    icon: "🚯",
    hint: "Waste dumped in an unauthorised place",
  },
  {
    value: "BROKEN_DRAINAGE",
    label: "Broken Drainage",
    icon: "🚰",
    hint: "Blocked drain, open manhole, or flooding",
  },
];

export const CATEGORY_BY_VALUE = Object.fromEntries(
  CATEGORIES.map((category) => [category.value, category])
);

export function categoryLabel(value) {
  return CATEGORY_BY_VALUE[value]?.label ?? value;
}

export function categoryIcon(value) {
  return CATEGORY_BY_VALUE[value]?.icon ?? "📍";
}

export const STATUSES = [
  {
    value: "SUBMITTED",
    label: "Submitted",
    tone: "info",
    description: "We have received your report.",
  },
  {
    value: "UNDER_REVIEW",
    label: "Under Review",
    tone: "warning",
    description: "A city officer is verifying the details.",
  },
  {
    value: "IN_PROGRESS",
    label: "In Progress",
    tone: "primary",
    description: "Work has started on this issue.",
  },
  {
    value: "RESOLVED",
    label: "Resolved",
    tone: "success",
    description: "The issue has been fixed.",
  },
  {
    value: "REJECTED",
    label: "Rejected",
    tone: "danger",
    description: "This report could not be actioned.",
  },
];

export const STATUS_BY_VALUE = Object.fromEntries(
  STATUSES.map((status) => [status.value, status])
);

// Map + chart encodings. Both palettes were validated for contrast and
// color-vision-deficiency separation on the dark admin surface; closed
// statuses additionally change marker style so state never rides on hue alone.
export const CATEGORY_COLORS = {
  WATER_LEAKAGE: "#3987e5",
  POTHOLE: "#d95926",
  BROKEN_DRAINAGE: "#199e70",
  STREETLIGHT: "#c98500",
  GARBAGE_OVERFLOW: "#d55181",
  ILLEGAL_DUMPING: "#008300",
  DAMAGED_PUBLIC_PROPERTY: "#9085e9",
};

export const STATUS_COLORS = {
  SUBMITTED: "#3987e5",
  UNDER_REVIEW: "#c98500",
  IN_PROGRESS: "#d55181",
  RESOLVED: "#0ca30c",
  REJECTED: "#d03b3b",
};

export function categoryColor(value) {
  return CATEGORY_COLORS[value] ?? "#3987e5";
}

export function statusColor(value) {
  return STATUS_COLORS[value] ?? "#3987e5";
}

export const CLOSED_STATUSES = ["RESOLVED", "REJECTED"];

export const STATUS_FLOW = ["SUBMITTED", "UNDER_REVIEW", "IN_PROGRESS", "RESOLVED"];

export function statusLabel(value) {
  return STATUS_BY_VALUE[value]?.label ?? value;
}

export const DESCRIPTION_MIN_LENGTH = 10;
export const DESCRIPTION_MAX_LENGTH = 2000;

export const MAX_PHOTO_BYTES = 5 * 1024 * 1024;
export const ACCEPTED_PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];
