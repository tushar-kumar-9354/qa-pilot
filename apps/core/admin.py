from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, TestSuite, TestCase, TestRun, BugReport


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'role', 'is_staff', 'created_at']
    list_filter = ['role', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('QA-Pilot', {'fields': ('role', 'bio')}),
    )


@admin.register(TestSuite)
class TestSuiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'owner', 'total_cases', 'pass_rate', 'created_at']
    list_filter = ['status']
    search_fields = ['name']


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ['name', 'suite', 'test_type', 'priority', 'is_ai_generated', 'created_at']
    list_filter = ['test_type', 'priority', 'is_ai_generated']
    search_fields = ['name']


@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    list_display = ['suite', 'status', 'result', 'passed', 'failed', 'pass_rate', 'created_at']
    list_filter = ['status', 'result']
    readonly_fields = ['logs']


@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'severity', 'status', 'test_run', 'created_at']
    list_filter = ['severity', 'status']
    search_fields = ['title']