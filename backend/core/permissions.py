from rest_framework.permissions import BasePermission

NO_PROFILE_MESSAGE = "This account has no ConnectHER profile (mentor or mentee)."


def get_role(user):
    """The user's role, or None if they have no Profile (e.g. the admin superuser)."""
    profile = getattr(user, "profile", None)  # RelatedObjectDoesNotExist is an AttributeError
    return profile.role if profile else None


class _RolePermission(BasePermission):
    role = None
    role_message = ""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False  # DRF turns this into a 401 for token auth
        user_role = get_role(user)
        if user_role is None:
            self.message = NO_PROFILE_MESSAGE
            return False
        self.message = self.role_message
        return user_role == self.role


class IsMentor(_RolePermission):
    role = "mentor"
    role_message = message = "Only mentors can do this."


class IsMentee(_RolePermission):
    role = "mentee"
    role_message = message = "Only mentees can ask questions."
