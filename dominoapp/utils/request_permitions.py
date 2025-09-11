from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, NotAuthenticated

class IsSuperAdminUser(permissions.BasePermission):
    """
    Allows access only to superadmin users.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise NotAuthenticated("Authentication credentials were not provided.")
        if not request.user.is_superuser:
            raise PermissionDenied("You do not have permission to perform this action.")
        return True