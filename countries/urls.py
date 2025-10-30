from django.urls import path
from . import views

urlpatterns = [
    path('countries/refresh', views.refresh_countries),
    path('countries', views.list_countries),
    # single endpoint handles GET and DELETE for a named country
    # serve the summary image before the dynamic name route so 'image' isn't treated as a country name
    path('countries/image', views.get_summary_image),
    path('countries/<str:name>', views.country_detail),
    path('status', views.status_view),
]
