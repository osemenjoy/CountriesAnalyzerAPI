import requests, random, datetime
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from django.conf import settings
from .models import Country, RefreshStatus

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

    for data in countries_data:
        currency_list = data.get("currencies") or []
        currency_code = currency_list[0].get("code") if currency_list else None
        exchange_rate = rates.get(currency_code)
        population = data.get("population") or 0

        if exchange_rate:
            random_val = random.randint(1000, 2000)
            estimated_gdp = (population * random_val) / exchange_rate
        else:
            estimated_gdp = 0

        Country.objects.update_or_create(
            name__iexact=data["name"],
            defaults={
                "name": data["name"],
                "capital": data.get("capital"),
                "region": data.get("region"),
                "population": population,
                "currency_code": currency_code,
                "exchange_rate": exchange_rate,
                "estimated_gdp": estimated_gdp,
                "flag_url": data.get("flag"),
            }
        )

    RefreshStatus.objects.update_or_create(id=1)
    generate_summary_image()
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
