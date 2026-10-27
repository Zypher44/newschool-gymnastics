from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, PublicEnquiry


class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Role Info', {'fields': ('role',)}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role Info', {'fields': ('role',)}),
    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')


admin.site.register(User, CustomUserAdmin)


@admin.register(PublicEnquiry)
class PublicEnquiryAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'kind', 'gym_name', 'name', 'status')
    list_filter = ('kind', 'status')
    readonly_fields = ('submission_id', 'created_at')

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission
