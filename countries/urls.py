from django.urls import path
from . import views

urlpatterns = [
    path('countries/refresh', views.refresh_countries),
    path('countries', views.list_countries),
    path('countries/<str:name>', views.get_country),
    path('countries/<str:name>', views.delete_country),
    path('status', views.status_view),
    path('countries/image', views.get_summary_image),
]
