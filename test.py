import unittest
from log_analyzer import *
import os
import gzip


class TestLogAnalyser(unittest.TestCase):

    def setUp(self):
        self.logs_dir = './test_data/log'
        self.reports_dir = './test_data/reports'

    def create_test_data(self, logs_list, log_data=b''):
        self.clear_test_data()
        os.makedirs(self.logs_dir)
        os.makedirs(self.reports_dir)
        for file_name in list(logs_list):
            with gzip.open(f'{self.logs_dir}/{file_name}', 'wb') as log:
                log.write(log_data)

    def clear_test_data(self):
        if os.path.isdir(self.logs_dir):
            for file_name in listdir(self.logs_dir):
                os.remove(os.path.join(self.logs_dir, file_name))
            os.rmdir(self.logs_dir)
        if os.path.isdir(self.reports_dir):
            for file_name in listdir(self.reports_dir):
                os.remove(os.path.join(self.reports_dir, file_name))
            os.rmdir(self.reports_dir)

    def test_get_last_log_gz(self):
        logs_list = [
            'nginx-access-ui.log-20161230.gz',
            'nginx-access-ui.log-20110125.gz',
            'nginx-access-ui.log-20170125.bz2',
            'nginx-access-ui.log-20161229',
            'nginx-access-ui.log20191230.gz'

        ]
        self.create_test_data(logs_list)
        last_date, last_file_name, last_file_ext = get_last_log(self.logs_dir)
        self.assertEqual(last_date, '20161230')
        self.assertEqual(last_file_name, f'{self.logs_dir}/nginx-access-ui.log-20161230.gz')
        self.assertEqual(last_file_ext, '.gz')
        self.clear_test_data()

    def test_get_last_log_plain(self):
        logs_list = [
            'nginx-access-ui.log-20161230',
            'nginx-access-ui.log-20110125.gz',
            'nginx-access-ui.log-20170125.bz2',
            'nginx-access-ui.log-20161229',
            'nginx-access-ui.log20191230.gz'

        ]
        self.create_test_data(logs_list)
        last_date, last_file_name, last_file_ext = get_last_log(self.logs_dir)
        self.assertEqual(last_date, '20161230')
        self.assertEqual(last_file_name, f'{self.logs_dir}/nginx-access-ui.log-20161230')
        self.assertEqual(last_file_ext, '')
        self.clear_test_data()

    def test_stat(self):
        log_name = 'nginx-access-ui.log-20161230.gz'
        log_data = '1.202.56.176 -  - [30/Jun/2017:00:35:15 +0300] "get url1 " 400 166 "-" "-" "-" "-" "-" 0.001' \
                   + '\n' + \
                   '1.202.56.176 -  - [30/Jun/2017:00:35:15 +0300] "get url2 " 400 166 "-" "-" "-" "-" "-" 0.002' \
                   + '\n' + \
                   '1.202.56.176 -  - [30/Jun/2017:00:35:15 +0300] "get url3 " 400 166 "-" "-" "-" "-" "-" 0.003' \
                   + '\n' + \
                   '1.202.56.176 -  - [30/Jun/2017:00:35:15 +0300] "get url4 " 7 400 166 "-" "-" "-" "-" "-" 0.004'
        log_data = log_data.encode('utf8')
        self.create_test_data([log_name], log_data)
        log = gzip.open(os.path.join(self.logs_dir, log_name))
        report_size = 2
        urls, total_cnt, corrupted_cnt, total_time = get_urls_info(log)
        table_stat = get_stat(urls, total_cnt, total_time, report_size)
        table_stat_test = [{'url': "url3", 'count': 1, 'count_perc': 25.0, 'time_sum': 0.003, 'time_perc': 50.0,
                            'time_avg': 0.003, 'time_max': 0.003, 'time_med': 0.003},
                           {'url': "url2", 'count': 1, 'count_perc': 25.0, 'time_sum': 0.002, 'time_perc': 33.333,
                            'time_avg': 0.002, 'time_max': 0.002, 'time_med': 0.002}]
        self.assertEqual(table_stat, table_stat_test)
        self.assertEqual(corrupted_cnt, 1)
        self.clear_test_data()


if __name__ == "__main__":
    unittest.main()
