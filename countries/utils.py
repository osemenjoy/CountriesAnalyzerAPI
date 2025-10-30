import requests, random, datetime
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from django.conf import settings
from .models import Country, RefreshStatus
from django.db import transaction

COUNTRY_API = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"
EXCHANGE_API = "https://open.er-api.com/v6/latest/USD"

def fetch_and_cache_countries():
    try:
        countries_resp = requests.get(COUNTRY_API, timeout=10)
        rates_resp = requests.get(EXCHANGE_API, timeout=10)
        countries_resp.raise_for_status()
        rates_resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": "External data source unavailable", "details": str(e)}, 503

    countries_data = countries_resp.json()
    rates = rates_resp.json().get("rates", {})
    # Persist changes atomically - if anything fails, rollback so we don't leave partial updates
    try:
        with transaction.atomic():
            for data in countries_data:
                currency_list = data.get("currencies") or []
                currency_code = currency_list[0].get("code") if currency_list else None
                population = data.get("population") or 0

                # currency handling per spec
                if not currency_code:
                    exchange_rate = None
                    estimated_gdp = 0
                else:
                    exchange_rate = rates.get(currency_code)
                    if exchange_rate is None:
                        # currency exists but no rate found
                        estimated_gdp = None
                    else:
                        random_val = random.randint(1000, 2000)
                        estimated_gdp = (population * random_val) / exchange_rate

                name = data["name"]
                attrs = {
                    "name": name,
                    "capital": data.get("capital"),
                    "region": data.get("region"),
                    "population": population,
                    "currency_code": currency_code,
                    "exchange_rate": exchange_rate,
                    "estimated_gdp": estimated_gdp,
                    "flag_url": data.get("flag"),
                }

                # match by name case-insensitively
                existing = Country.objects.filter(name__iexact=name).first()
                if existing:
                    for k, v in attrs.items():
                        setattr(existing, k, v)
                    existing.save()
                else:
                    Country.objects.create(**attrs)

            # update or create global refresh status (auto_now will update timestamp)
            RefreshStatus.objects.update_or_create(id=1, defaults={})

            # generate the summary image after successful DB update
            generate_summary_image()

    except Exception:
        # Re-raise so callers can decide how to respond; transaction.atomic will roll back
        raise

    return {"message": "Countries refreshed successfully"}

def generate_summary_image():
    top_countries = Country.objects.exclude(estimated_gdp__isnull=True).order_by('-estimated_gdp')[:5]
    total = Country.objects.count()
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((20, 20), f"Total Countries: {total}", fill="black")
    draw.text((20, 60), "Top 5 by GDP:", fill="black")

    y = 100
    for c in top_countries:
        draw.text((40, y), f"{c.name}: {round(c.estimated_gdp, 2)}", fill="black")
        y += 30

    draw.text((20, 300), f"Last Refresh: {timestamp}", fill="gray")

    img.save("cache/summary.png")
