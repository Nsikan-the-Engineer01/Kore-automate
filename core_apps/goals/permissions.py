from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Object-level permission to only allow users to access their own goals.
    
    Checks that the requesting user is the owner of the goal object.
    """
    
    message = "You do not have permission to access this goal. It belongs to another user."
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the requesting user owns the goal object.
        
        Args:
            request: The HTTP request object
            view: The view being accessed
            obj: The goal object being accessed
            
        Returns:
            bool: True if request.user is the owner, False otherwise
        """
        return obj.user == request.user
