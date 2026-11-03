import unittest
from unittest.mock import Mock, patch

import requests
from app import app


class LeadFormTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.data = {
            'entry.659206793': '测试联系人',
            'entry.649232157': '13800000000',
            'entry.1105577049': '了解产品',
            'consent': 'on',
        }

    @patch('app.requests.post')
    def test_only_confirmed_response_is_success(self, post):
        post.return_value = Mock(status_code=200, text='<div class="vHW8K">Your response has been recorded.</div>')
        response = self.client.post('/api/lead', data=self.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'ok': True})
        self.assertIn('no-store', response.headers['Cache-Control'])
        for key, value in self.data.items():
            if key != 'consent':
                self.assertEqual(post.call_args.kwargs['data'][key], value)
        self.assertNotIn('consent', post.call_args.kwargs['data'])

    @patch('app.requests.post')
    def test_loaded_error_page_is_not_success(self, post):
        post.return_value = Mock(status_code=200, text='<form>This is a required question</form>')
        response = self.client.post('/api/lead', data=self.data)
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.json['ok'])

    @patch('app.requests.post')
    def test_one_contact_records_its_type(self, post):
        post.return_value = Mock(status_code=200, text='<div class="vHW8K">Your response has been recorded.</div>')
        for contact_type, contact, expected in [('phone', '13800000000', '13800000000'), ('wechat', 'wx_demo', '微信号：wx_demo'), ('telegram', '@demo', 'TG号：@demo')]:
            response = self.client.post('/api/lead', data={**self.data, 'contact_type': contact_type, 'entry.649232157': contact})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(post.call_args.kwargs['data']['entry.649232157'], expected)
            self.assertNotIn('contact_type', post.call_args.kwargs['data'])

    @patch('app.requests.post')
    def test_invalid_contacts_never_reach_google(self, post):
        for contact_type in ('phone', 'wechat', 'telegram', 'unknown', ''):
            for contact in ('', ' ', 'a' * 65):
                self.assertEqual(self.client.post('/api/lead', data={**self.data, 'contact_type': contact_type, 'entry.649232157': contact}).status_code, 400)
        for contact_type in ('unknown', ''):
            self.assertEqual(self.client.post('/api/lead', data={**self.data, 'contact_type': contact_type}).status_code, 400)
        self.assertEqual(self.client.post('/api/lead', data={**self.data, 'entry.649232157': '1' * 33}).status_code, 400)
        post.assert_not_called()

    @patch('app.requests.post')
    def test_optional_city_preserves_company_and_details(self, post):
        post.return_value = Mock(status_code=200, text='<div class="vHW8K">Your response has been recorded.</div>')
        for city, details in [(None, '说明'), ('   ', '说明'), (' 杭州 ', '说明'), ('深圳', ''), ('a' * 100, 'a' * 2000)]:
            data = {**self.data, 'entry.1259853372': '测试公司', 'entry.853679754': details}
            if city is not None:
                data['company_city'] = city
            self.assertEqual(self.client.post('/api/lead', data=data).status_code, 200)
            posted = post.call_args.kwargs['data']
            self.assertEqual(posted['entry.562954983'], (city or '').strip())
            self.assertEqual(posted['entry.853679754'], details)
            self.assertEqual(posted['entry.1259853372'], '测试公司')
            self.assertNotIn('company_city', posted)

    @patch('app.requests.post')
    def test_oversized_city_never_reaches_google(self, post):
        self.assertEqual(self.client.post('/api/lead', data={**self.data, 'company_city': 'a' * 101}).status_code, 400)
        post.assert_not_called()

    @patch('app.requests.post', side_effect=requests.Timeout)
    def test_timeout_does_not_report_success_or_retry(self, post):
        response = self.client.post('/api/lead', data=self.data)
        self.assertEqual(response.status_code, 504)
        self.assertFalse(response.json['ok'])
        post.assert_called_once()

    @patch('app.requests.post')
    def test_invalid_input_never_reaches_google(self, post):
        for values in [{}, {**self.data, 'consent': ''}, {**self.data, 'entry.659206793': ' '}]:
            self.assertEqual(self.client.post('/api/lead', data=values, content_type='application/x-www-form-urlencoded').status_code, 400)
        post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
