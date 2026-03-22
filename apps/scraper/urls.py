from django.urls import path
from . import views

urlpatterns = [
    path('trigger', views.trigger_scraper, name='trigger_scraper'),
    path('data', views.list_scraped_data, name='list_scraped_data'),
]