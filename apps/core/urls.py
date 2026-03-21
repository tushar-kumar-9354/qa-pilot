from django.urls import path
from . import views

urlpatterns = [
    # ── Pages ───────────────────────────────────────────────
    path('', views.dashboard, name='dashboard'),
    path('suites/', views.suites, name='suites'),
    path('runs/', views.runs, name='runs'),
    path('bugs/', views.bugs, name='bugs'),
    path('data/', views.scraped_data, name='scraped_data'),
    path('scraper/', views.scraper, name='scraper'),
    path('agents/generate/', views.agent_generate, name='agent_generate'),
    path('agents/chat/', views.agent_chat, name='agent_chat'),
    path('agents/healer/', views.agent_healer, name='agent_healer'),

    # ── Django-direct APIs (no FastAPI needed) ───────────────
    path('api/health/', views.api_health, name='api_health'),
    path('api/dashboard/stats', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/suites', views.api_suites, name='api_suites'),
    path('api/runs', views.api_runs, name='api_runs'),
    path('api/runs/trigger', views.api_trigger_run, name='api_trigger_run'),
    path('api/scraper/data', views.api_scraper_data, name='api_scraper_data'),
    path('api/scraper/trigger', views.api_scraper_trigger, name='api_scraper_trigger'),

    # ── AI Agents ────────────────────────────────────────────
    path('api/agents/chat', views.api_chat, name='api_chat'),
    path('api/agents/generate-tests', views.api_generate_tests, name='api_generate_tests'),
    path('api/agents/heal-selector', views.api_heal_selector, name='api_heal_selector'),
    path('api/agents/analyze-failure', views.api_analyze_failure, name='api_analyze_failure'),
    path('api/scraper/record/<str:record_id>', views.api_scraper_record, name='api_scraper_record'),
]
