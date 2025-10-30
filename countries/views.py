from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Country, RefreshStatus
from .serializers import CountrySerializer
from .utils import fetch_and_cache_countries
import os

@api_view(['POST'])
def refresh_countries(request):
    # reference request to satisfy linters while still accepting the DRF request param
    assert request is not None
    try:
        # fetch_and_cache_countries performs its own atomic DB updates.
        data = fetch_and_cache_countries()
    except Exception as e:
        # keep DB intact if external fetch fails
        return Response({"error": "External data source unavailable", "details": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    # success
    return Response(data, status=status.HTTP_200_OK)

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

@api_view(['GET', 'DELETE'])
def country_detail(request, name):
    """Handle GET and DELETE for a single country by name (case-insensitive)."""
    if request.method == 'GET':
        try:
            country = Country.objects.get(name__iexact=name)
        except Country.DoesNotExist:
            return Response({"error": "Country not found"}, status=404)

        serializer = CountrySerializer(country)
        return Response(serializer.data)

    if request.method == 'DELETE':
        country_qs = Country.objects.filter(name__iexact=name)
        if not country_qs.exists():
            return Response({"error": "Country not found"}, status=404)
        country_qs.delete()
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
    # reference request to satisfy linters while still accepting the DRF request param
    assert request is not None
    image_path = "cache/summary.png"
    if not os.path.exists(image_path):
        return Response({"error": "Summary image not found"}, status=404)
    from django.http import FileResponse
    return FileResponse(open(image_path, 'rb'), content_type='image/png')
