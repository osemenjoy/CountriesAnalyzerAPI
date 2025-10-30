from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Country, RefreshStatus
from .serializers import CountrySerializer
from .utils import fetch_and_cache_countries
import os

@api_view(['POST'])
def refresh_countries(request):
    data, code = fetch_and_cache_countries(), 200
    if isinstance(data, tuple):  # means error
        return Response(data[0], status=data[1])
    return Response(data, status=code)

@api_view(['GET'])
def list_countries(request):
    queryset = Country.objects.all()
    region = request.GET.get('region')
    currency = request.GET.get('currency')
    sort = request.GET.get('sort')

    if region:
        queryset = queryset.filter(region__iexact=region)
    if currency:
        queryset = queryset.filter(currency_code__iexact=currency)
    if sort == 'gdp_desc':
        queryset = queryset.order_by('-estimated_gdp')

    serializer = CountrySerializer(queryset, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_country(request, name):
    country = get_object_or_404(Country, name__iexact=name)
    serializer = CountrySerializer(country)
    return Response(serializer.data)

@api_view(['DELETE'])
def delete_country(request, name):
    country = Country.objects.filter(name__iexact=name)
    if not country.exists():
        return Response({"error": "Country not found"}, status=404)
    country.delete()
    return Response(status=204)

@api_view(['GET'])
def status_view(request):
    total = Country.objects.count()
    refresh = RefreshStatus.objects.first()
    return Response({
        "total_countries": total,
        "last_refreshed_at": refresh.last_refreshed_at if refresh else None
    })

@api_view(['GET'])
def get_summary_image(request):
    image_path = "cache/summary.png"
    if not os.path.exists(image_path):
        return Response({"error": "Summary image not found"}, status=404)
    from django.http import FileResponse
    return FileResponse(open(image_path, 'rb'), content_type='image/png')
