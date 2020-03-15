#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';
import gzip
from os import listdir, stat
from os.path import join, exists
import re
from string import Template
import argparse
import json
import logging
from datetime import datetime


default_config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "APP_LOGFILE": None
}

CORRUPT_PERCENT = 0.2
LOG_NAME_PATTERN = r'^nginx-access-ui\.log-(\d{8})(\.gz|)$'
LOG_LINE_PATTERN = r'^(\d|\.)+ .+  .+ \[.+] ".+" \d+ \d+ ".+" ".+" ".+" ".+" \d+\.\d+$'


def insert_sorted(sorted_list, new_elem):
    left = 0
    right = len(sorted_list)
    while left != right:
        mid = left + (right - left) // 2
        if sorted_list[mid] == new_elem:
            left = right = mid
        elif sorted_list[mid] < new_elem:
            left = mid + 1
        else:
            right = mid
    return sorted_list[:left] + [new_elem] + sorted_list[left:]


def median(sorted_list):
    if len(sorted_list) > 1:
        return (sorted_list[(len(sorted_list) - 1) // 2] + sorted_list[len(sorted_list) // 2]) / 2
    else:
        return sorted_list[0]


def get_last_log(directory):
    last_date = last_file_name = last_file_ext = None
    for file_name in listdir(directory):
        match = re.search(LOG_NAME_PATTERN, file_name)
        if match:
            file_date = match.group(1)
            if not last_date or file_date > last_date:
                last_date = file_date
                last_file_ext = match.group(2)
                last_file_name = join(directory, file_name)
    return last_date, last_file_name, last_file_ext


def parse(log_file):
    for line in log_file:
        line = str(line, 'utf8')
        url = request_time = None
        if re.match(LOG_LINE_PATTERN, line):
            url_start = line.find(' ', line.find('"') + 1) + 1
            url_end = line.find(' ', url_start)
            url = line[url_start: url_end]
            request_time = float(line[line.rfind(' ') + 1:])
        yield url, request_time


def get_urls_info(log_file):
    url_info = dict()
    total_cnt = total_time = corrupted_cnt = 0
    lines = parse(log_file)
    for url, request_time in lines:
        if not url:
            corrupted_cnt += 1
        elif url not in url_info.keys():
            url_info[url] = [request_time]
        else:
            url_info[url] = insert_sorted(url_info[url], request_time)
        total_time += request_time
        total_cnt += 1
    return url_info, total_cnt, corrupted_cnt, total_time


def get_stat(url_info, total_cnt, total_time, report_size):
    table_stat = []
    url_info.pop("", None)
    for url in url_info.keys():
        statistics = dict()
        statistics["url"] = url
        statistics["count"] = len(url_info[url])
        statistics["count_perc"] = round(100 * len(url_info[url]) / total_cnt, 3)
        statistics["time_sum"] = round(sum(url_info[url]), 3)
        statistics["time_perc"] = round(100 * sum(url_info[url]) / total_time, 3)
        statistics["time_avg"] = round(sum(url_info[url]) / len(url_info[url]), 3)
        statistics["time_max"] = round(url_info[url][-1], 3)
        statistics["time_med"] = round(median(url_info[url]), 3)
        table_stat.append(statistics)
    table_stat.sort(reverse=True, key=lambda x: x['time_sum'])
    return table_stat[:report_size]


def get_report_name(log_date):
    if log_date:
        report_date = datetime.strptime(log_date, '%Y%m%d').strftime('%Y.%m.%d')
        return f'report-{report_date}.html'


def generate_report(table_stat, report_name):
    with open('report.html', 'r') as report_template:
        template_text = report_template.read()
        report_text = Template(template_text).safe_substitute(table_json=table_stat)
    with open(join(default_config['REPORT_DIR'], report_name), 'w+') as report:
        report.write(report_text)


def get_config(config, config_file_path):
    with open(config_file_path) as config_file:
        if stat(config_file_path).st_size != 0:
            config_from_file = json.load(config_file)
        else:
            config_from_file = {}
    config.update(config_from_file)
    return config


def main(config):
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", default='./config.json')
        args = parser.parse_args()
        config_path = args.config
        config = get_config(config, config_path)
        app_log_file = config['APP_LOGFILE']
        logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s',
                            level='INFO',
                            datefmt='%Y.%m.%d %H:%M:%S',
                            filename=app_log_file)
        report_dir, log_dir, report_size = config['REPORT_DIR'], config['LOG_DIR'], config['REPORT_SIZE']
        logging.info(msg='Start working')
        log_date, log_name, log_ext = get_last_log(log_dir)
        report_name = get_report_name(log_date)
        if not log_date:
            logging.info(msg='No logs to process')
        elif exists(join(report_dir, report_name)):
            logging.info(msg='Report already exists')
        else:
            log = gzip.open(log_name) if log_ext == '.gz' else open(log_name)
            urls, total_cnt, corrupted_cnt, total_time = get_urls_info(log)
            if corrupted_cnt / total_cnt > CORRUPT_PERCENT:
                logging.info(msg='Too much corrupted lines')
            else:
                table_stat = get_stat(urls, total_cnt, total_time, report_size)
                generate_report(table_stat, report_name)
                logging.info(msg='Done')
            log.close()
    except KeyboardInterrupt as e:
        logging.exception(e, exc_info=True)
    except Exception as e:
        logging.exception(e, exc_info=True)


if __name__ == "__main__":
    main(default_config)
