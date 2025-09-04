#!/usr/bin/env python3

import json
import tempfile
import shutil
import urllib.request
import os
import sys
import argparse
from http.server import HTTPServer
from http.server import CGIHTTPRequestHandler
from urllib.parse import urljoin
from uuid import uuid4
from threading import Thread
from os import path
from os.path import join
import requests

from symbols_server_common import *

port = 80
cgi_folder_name = 'cgi-bin'
history_file_path = '000Admin/history.txt'
symstore_root_looking = 'C:\\Program Files (x86)\\Windows Kits\\'
symstore_exe_name = 'symstore.exe'


def get_server():
    handler = CGIHTTPRequestHandler
    handler.cgi_directories = ["/" + cgi_folder_name]
    return HTTPServer(("", port), handler)


class Tests:
    test_symbols_folder_name = "symbols_test_" + str(uuid4())
    test_symbols_path = join(os.curdir, test_symbols_folder_name)
    proxy_info = {
        "http": "",
        "https": "",
    }

    def __init__(self):
        pass

    @staticmethod
    def get_server_address():
        return "http://localhost:" + str(port) + "/"

    def get_cgi_address(self):
        return urljoin(self.get_server_address(), cgi_folder_name + "/")

    def get_symbols_address(self):
        return urljoin(self.get_server_address(), self.test_symbols_folder_name + "/")

    def test_add_symbols_and_check_availability(self):
        # prepare
        product_name = 'test_product_name'
        product_version = 'a_random_version 1.2.3.4'
        comment = 'whatever comments !!!'
        tmp_dir = join(tempfile.gettempdir(), str(uuid4()))
        os.mkdir(tmp_dir)
        response = requests.get(
            "https://www.nuget.org/api/v2/package/System.Reactive/4.1.3",
            proxies=self.proxy_info)
        zip_path = join(tmp_dir, "System.Reactive-4.1.3.nupkg")
        with open(zip_path, "wb") as zip_file_output:
            zip_file_output.write(response.content)

        # act
        with open(zip_path, 'rb') as zip_file_input:
            result = requests.post(
                urljoin(self.get_cgi_address(), "add.py"),
                files={
                    Fields.zip: zip_file_input,
                    Fields.product_name: product_name,
                    Fields.product_version: product_version,
                    Fields.comment: comment})
            # print('result.content=' + result.content.decode('utf-8'))
            json_result = json.loads(result.content.decode('utf-8'))
            assert json_result["status"] == "success", json_result["message"]
        dll_url = urljoin(self.get_symbols_address(), "System.Reactive.dll/A3630135134000/System.Reactive.dl_")
        answer = urllib.request.urlopen(dll_url).read()
        assert b"error" not in answer
        assert b"Error" not in answer
        assert b"ERROR" not in answer
        assert answer != b""
        history_url = urljoin(self.get_symbols_address(), history_file_path)
        history = str.split(urllib.request.urlopen(history_url).read().decode('utf-8'), ',')
        print("History: " + str(history))
        assert Tests.clean_history_value(history[5]) == product_name
        assert Tests.clean_history_value(history[6]) == product_version
        assert Tests.clean_history_value(history[7]) == comment

        # clean-up
        shutil.rmtree(tmp_dir)

    @staticmethod
    def clean_history_value(value):
        return value.replace('"', '')

    def run(self):
        print("Starting test")
        Env.set_symbols_repo_path(self.test_symbols_path)
        os.mkdir(self.test_symbols_path)
        server = get_server()

        def threaded_function():
            server.serve_forever()

        thread = Thread(target=threaded_function)
        thread.start()

        try:
            self.test_add_symbols_and_check_availability()
        finally:
            server.shutdown()
            thread.join()

        shutil.rmtree(self.test_symbols_path)

        print("Test done")


def start_server(symbols_path=None):
    configure_symbols_path(symbols_path)
    get_server().serve_forever()


def parse_arguments():
    parser = argparse.ArgumentParser(description='Symbols Server')
    parser.add_argument('--symbols-path',
                       type=str,
                       required=True,
                       help='Path to the symbols directory')
    parser.add_argument('--test',
                       action='store_true',
                       help='Run tests (uses temporary directory)')
    return parser, parser.parse_args()


def configure_symbols_path(symbols_path):
    if not path.exists(symbols_path):
        os.makedirs(symbols_path)
        print("Created symbols directory: " + symbols_path)

    Env.set_symbols_repo_path(symbols_path)
    print("Using symbols repository path: " + symbols_path)


def find_symstore():
    for root, dirs, files in os.walk(symstore_root_looking):
        for f in files:
            if f == symstore_exe_name and 'x64' in root:
                return join(root, f)
    return None


def configure_symstore():
    symstore_path = find_symstore()
    if symstore_path is None:
        raise Exception("Symstore isn't found.")
    Env.set_symstore_path(symstore_path)
    print("Using symstore path: " + symstore_path)


if __name__ == '__main__':
    parser, args = parse_arguments()

    configure_symstore()

    if args.test:
        print("Running tests...")
        Tests().run()
    else:
        start_server(args.symbols_path)
