from django.db import models

class Country(models.Model):
    name = models.CharField(max_length=255, unique=True)
    capital = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=255, null=True, blank=True)
    population = models.BigIntegerField()
    currency_code = models.CharField(max_length=10, null=True, blank=True)
    exchange_rate = models.FloatField(null=True, blank=True)
    estimated_gdp = models.FloatField(null=True, blank=True)
    flag_url = models.URLField(null=True, blank=True)
    last_refreshed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class RefreshStatus(models.Model):
    last_refreshed_at = models.DateTimeField(auto_now=True)
