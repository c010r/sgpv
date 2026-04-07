from rest_framework.permissions import BasePermission


class IsRoleIn(BasePermission):
    allowed_roles = set()

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in self.allowed_roles


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == "SUPERADMIN"


class IsSupervisorOrAbove(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in {"SUPERADMIN", "SUPERVISOR"}


class IsCajeroOrAbove(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in {
            "SUPERADMIN",
            "SUPERVISOR",
            "CAJERO",
        }
