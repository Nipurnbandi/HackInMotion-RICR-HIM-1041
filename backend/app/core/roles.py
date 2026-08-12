import enum


class Role(str, enum.Enum):
    CITIZEN = "CITIZEN"
    ADMIN = "ADMIN"
