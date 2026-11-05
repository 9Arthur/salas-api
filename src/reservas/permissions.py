from rest_framework.permissions import BasePermission


class EhDonoOuAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.usuario_id == request.user.id
