from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Country, RefreshStatus
from .serializers import CountrySerializer
from .utils import fetch_and_cache_countries
from django.http import FileResponse
import os

# ----------------------------
# POST /countries/refresh
# ----------------------------
@api_view(['POST'])
def refresh_countries(request):
    """
    Refresh the country dataset by fetching from the external API.
    Clears existing countries, then re-caches fresh data.
    """
    assert request is not None

    try:
        # Step 1: clear existing data outside of any atomic transaction
        Country.objects.all().delete()

        # Step 2: fetch and cache new countries
        data = fetch_and_cache_countries()

        # Step 3: if the util returned (payload, code) -> error case
        if isinstance(data, tuple):
            return Response(data[0], status=data[1])

        # Step 4: update refresh timestamp
        RefreshStatus.objects.update_or_create(id=1, defaults={})
        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": "External data source unavailable", "details": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


# ----------------------------
# GET /countries
# ----------------------------
@api_view(['GET'])
def list_countries(request):
    """
    List all countries, with optional filters and sorting.
    Supports:
        - ?region=Asia
        - ?currency=USD
        - ?sort=gdp_desc
    """
    try:
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
    except Exception as e:
          return Response(
            {"error": "An error occurred", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ----------------------------
# GET /countries/:name
# DELETE /countries/:name
# ----------------------------
@api_view(['GET', 'DELETE'])
def country_detail(request, name):
    """
    Handle GET and DELETE for a single country by name (case-insensitive).
    """
    try:
        country = Country.objects.get(name__iexact=name)
    except Country.DoesNotExist:
        return Response({"error": "Country not found"}, status=404)

    try:
        if request.method == 'GET':
            serializer = CountrySerializer(country)
            return Response(serializer.data)

        if request.method == 'DELETE':
            country.delete()
            return Response({"message": "Country deleted successfully"}, status=204)
    except Exception as e:
        return Response(
            {"error": "An error occurred", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ----------------------------
# GET /status
# ----------------------------
@api_view(['GET'])
def status_view(request):
    """
    Return the current dataset statistics.
    """
    try:
        total = Country.objects.count()
        refresh = RefreshStatus.objects.first()
        return Response({
            "total_countries": total,
            "last_refreshed_at": refresh.last_refreshed_at if refresh else None
        })
    except Exception as e:
        return Response(
            {"error": "An error occurred", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ----------------------------
# GET /countries/image
# ----------------------------
@api_view(['GET'])
def get_summary_image(request):
    """
    Return a generated summary image (PNG) of the countries data.
    """
    assert request is not None
    image_path = "cache/summary.png"

    if not os.path.exists(image_path):
        return Response({"error": "Summary image not found"}, status=404)

    return FileResponse(open(image_path, 'rb'), content_type='image/png')
