"""
Custom permissions for MALCHA-DAGU.
"""

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    객체의 소유자만 수정/삭제 가능.
    읽기(GET, HEAD, OPTIONS)는 모두 허용.
    
    IDOR(Insecure Direct Object Reference) 공격 방지.
    """
    
    def has_object_permission(self, request, view, obj):
        # 읽기 권한은 모두 허용 (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 쓰기 권한은 owner_id가 현재 유저와 일치하는 경우만 허용
        # owner_id가 None이면 (익명 등록) 거부
        if not hasattr(obj, 'owner_id') or obj.owner_id is None:
            return False
            
        return obj.owner_id == request.user.id
