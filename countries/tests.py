from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest import mock
from .models import Country, RefreshStatus
import io
import os


class CountriesAPITestCase(TestCase):
	"""Tests for the countries API endpoints following HNG standards.

	Covered endpoints:
	- POST /api/countries/refresh
	- GET  /api/countries
	- GET  /api/countries/<name>
	- DELETE /api/countries/<name>
	- GET /api/status
	- GET /api/countries/image
	"""

	def setUp(self):
		self.client = APIClient()
		# create some countries for list/get/delete/status
		Country.objects.create(
			name="Testland",
			capital="Testville",
			region="Test Region",
			population=1000,
			currency_code="TST",
			exchange_rate=2.0,
			estimated_gdp=500.0,
			flag_url="http://example.com/flag.png",
		)

		Country.objects.create(
			name="Samplestan",
			capital="Sample City",
			region="Sample Region",
			population=2000,
			currency_code="SMP",
			exchange_rate=4.0,
			estimated_gdp=1000.0,
			flag_url="http://example.com/flag2.png",
		)

		RefreshStatus.objects.create()  # ensure a refresh exists for status endpoint

	def test_list_countries_basic(self):
		resp = self.client.get('/countries')
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertIsInstance(resp.json(), list)
		self.assertGreaterEqual(len(resp.json()), 2)

	def test_list_countries_filters_and_sort(self):
		# filter by region
		resp = self.client.get('/countries', {'region': 'Sample Region'})
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		data = resp.json()
		self.assertEqual(len(data), 1)
		self.assertEqual(data[0]['name'], 'Samplestan')

		# filter by currency (case-insensitive)
		resp = self.client.get('/countries', {'currency': 'tst'})
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		data = resp.json()
		self.assertEqual(len(data), 1)
		self.assertEqual(data[0]['name'], 'Testland')

		# sort by gdp_desc
		resp = self.client.get('/countries', {'sort': 'gdp_desc'})
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		data = resp.json()
		# first should be Samplestan (1000.0) then Testland (500.0)
		self.assertGreaterEqual(float(data[0]['estimated_gdp']), float(data[1]['estimated_gdp']))

	def test_get_country_success_and_not_found(self):
		resp = self.client.get('/countries/Testland')
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertEqual(resp.json()['name'], 'Testland')

		# not found
		resp = self.client.get('/countries/NoSuchCountry')
		self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
		self.assertIn('error', resp.json())

	def test_delete_country_success_and_not_found(self):
		resp = self.client.delete('/countries/Samplestan')
		self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
		# subsequent delete should return 404
		resp = self.client.delete('/countries/Samplestan')
		self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
		self.assertIn('error', resp.json())

	def test_status_view(self):
		resp = self.client.get('/status')
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		data = resp.json()
		self.assertIn('total_countries', data)
		self.assertIn('last_refreshed_at', data)
		self.assertGreaterEqual(data['total_countries'], 2)

	@override_settings(MEDIA_ROOT=os.path.join(os.getcwd(), 'cache'))
	def test_get_summary_image_not_found_and_found(self):
		# ensure cache dir exists and remove any existing image
		cache_dir = os.path.join(os.getcwd(), 'cache')
		os.makedirs(cache_dir, exist_ok=True)
		image_path = os.path.join(cache_dir, 'summary.png')
		if os.path.exists(image_path):
			os.remove(image_path)

		resp = self.client.get('/countries/image')
		self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

		# create a fake image file and try again
		with open(image_path, 'wb') as f:
			f.write(b'PNGDATA')

		resp = self.client.get('/countries/image')
		# FileResponse returns 200 (or 200-ish), check for OK
		self.assertIn(resp.status_code, (status.HTTP_200_OK,))

	@mock.patch('countries.utils.requests.get')
	@mock.patch('countries.utils.generate_summary_image')
	def test_refresh_countries_success_and_external_failure(self, mock_generate, mock_get):
		# successful external calls mock
		class FakeResp:
			def __init__(self, json_data, status=200):
				self._json = json_data
				self.status_code = status

			def json(self):
				return self._json

			def raise_for_status(self):
				if not (200 <= self.status_code < 300):
					raise Exception('bad')

		# first call returns a simplified countries list, second returns rates
		def side_effect(url, timeout=10):
			if 'restcountries' in url:
				return FakeResp([
					{
						'name': 'Mockland',
						'capital': 'Mock City',
						'region': 'Mock Region',
						'population': 500,
						'flag': 'http://example.com/flag.png',
						'currencies': [{'code': 'USD'}]
					}
				])
			else:
				return FakeResp({'rates': {'USD': 1.0}})

		mock_get.side_effect = side_effect

		resp = self.client.post('/countries/refresh')
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertIn('message', resp.json())
		self.assertIn('message', resp.json())

		# simulate external failure
		# simulate external failure using RequestException which utils will propagate
		import requests as _req
		mock_get.side_effect = _req.exceptions.RequestException('network error')
		resp = self.client.post('/countries/refresh')
		self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
		self.assertIn('error', resp.json())

