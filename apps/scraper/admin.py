from django.contrib import admin
from .models import ScraperTarget, ScraperRun, ScrapedData


@admin.register(ScraperTarget)
class ScraperTargetAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'data_type', 'is_active', 'total_records_scraped', 'last_scraped_at']
    list_filter = ['data_type', 'is_active']


@admin.register(ScraperRun)
class ScraperRunAdmin(admin.ModelAdmin):
    list_display = ['target', 'status', 'records_scraped', 'started_at', 'completed_at']
    list_filter = ['status']


@admin.register(ScrapedData)
class ScrapedDataAdmin(admin.ModelAdmin):
    list_display = ['title', 'target', 'row_count', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['title']