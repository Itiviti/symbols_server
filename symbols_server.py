#!/usr/bin/env python3

import json
import tempfile
import shutil
import urllib.request
import os
import sys
import argparse
import zipfile
import subprocess
from urllib.parse import urljoin, urlparse
from uuid import uuid4
from threading import Thread
from os import path
from os.path import join
import requests
from flask import Flask, request, jsonify, send_from_directory, send_file

from symbols_server_common import *

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024  # 100MB max file size

cgi_folder_name = 'cgi-bin'
history_file_path = '000Admin/history.txt'
symstore_root_looking = 'C:\\Program Files (x86)\\Windows Kits\\'
symstore_exe_name = 'symstore.exe'


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/symbols')
@app.route('/symbols/')
@app.route('/symbols/<path:filename>')
def serve_symbols(filename=''):
    symbols_repo = Env.get_symbol_repo_path()
    full_path = join(symbols_repo, filename) if filename else symbols_repo

    if os.path.isfile(full_path):
        return send_file(full_path)
    elif os.path.isdir(full_path):
        try:
            files = []
            dirs = []
            for item in os.listdir(full_path):
                item_path = join(full_path, item)
                if os.path.isdir(item_path):
                    dirs.append(item + '/')
                else:
                    files.append(item)

            html = f"""<!DOCTYPE html>
<html>
<head><title>Index of /symbols/{filename}</title></head>
<body>
<h1>Index of /symbols/{filename}</h1>
<hr>
<pre>
"""
            if filename:
                html += '<a href="../">../</a>\n'

            for dir_name in sorted(dirs):
                url = f"/symbols/{filename}/{dir_name}" if filename else f"/symbols/{dir_name}"
                html += f'<a href="{url}">{dir_name}</a>\n'

            for file_name in sorted(files):
                url = f"/symbols/{filename}/{file_name}" if filename else f"/symbols/{file_name}"
                html += f'<a href="{url}">{file_name}</a>\n'

            html += """</pre>
<hr>
</body>
</html>"""
            return html
        except Exception as e:
            return f"Error listing directory: {str(e)}", 500
    else:
        return "File not found", 404


# Needed to support /cgi-bin/add.py as the symstore plugin expects this path
@app.route('/cgi-bin/add.py', methods=['POST'])
def add_symbols():
    try:
        if 'zip' not in request.files:
            return jsonify({"status": "error", "message": "No zip file provided"}), 400

        zip_file = request.files['zip']
        if zip_file.filename == '':
            return jsonify({"status": "error", "message": "No file selected"}), 400

        product_name = request.form.get('product_name', '')
        product_version = request.form.get('product_version', '')
        comment = request.form.get('comment', '')

        tmp_dir = join(tempfile.gettempdir(), "symbols_server_" + str(uuid4()))
        os.mkdir(tmp_dir)

        try:
            zip_path = join(tmp_dir, zip_file.filename)
            zip_file.save(zip_path)

            if os.path.getsize(zip_path) == 0:
                raise Exception("File is empty")

            output_dir = join(tmp_dir, str(uuid4()))
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(output_dir)

            comment_to_use = comment if comment else zip_file.filename
            args = [Env.get_symstore_path(), "add",
                    "/compress",
                    "/r", "/f", output_dir,
                    "/s", Env.get_symbol_repo_path(),
                    "/t", product_name,
                    "/v", product_version,
                    "/c", comment_to_use]

            print("Running command: " + " ".join(args))
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise Exception(f"Command: {' '.join(args)} -- Output: {stdout.decode()} -- Errors: {stderr.decode()}")

            return jsonify({"status": "success"})

        finally:
            shutil.rmtree(tmp_dir)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


class Tests:
    test_symbols_folder_name = "symbols_test_" + str(uuid4())
    test_symbols_path = join(os.curdir, test_symbols_folder_name)
    proxy_info = {
        "http": "",
        "https": "",
    }

    def __init__(self):
        self.test_port = None

    def get_server_address(self):
        return "http://localhost:" + str(self.test_port) + "/"

    def get_cgi_address(self):
        return urljoin(self.get_server_address(), cgi_folder_name + "/")

    def get_symbols_address(self):
        return urljoin(self.get_server_address(), "symbols/")

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
                self.get_server_address() + "add",
                files={
                    Fields.zip: zip_file_input
                },
                data={
                    Fields.product_name: product_name,
                    Fields.product_version: product_version,
                    Fields.comment: comment
                })
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

        self.test_port = 51729

        import threading

        def run_flask():
            app.run(host='localhost', port=self.test_port, debug=False, use_reloader=False)

        thread = threading.Thread(target=run_flask)
        thread.daemon = True
        thread.start()

        import time
        time.sleep(1)

        try:
            self.test_add_symbols_and_check_availability()
        finally:
            pass  # Flask server will stop when thread ends

        shutil.rmtree(self.test_symbols_path)

        print("Test done")


def start_server(symbols_path, port_num):
    configure_symbols_path(symbols_path)
    print(f"Flask server starting on port {port_num}")
    app.run(host='0.0.0.0', port=port_num, debug=False)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Symbols Server')
    parser.add_argument('--symbols-path',
                       type=str,
                       help='Path to the symbols directory (not required for tests)')
    parser.add_argument('--port',
                       type=int,
                       default=80,
                       help='Port number (default: 80)')
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
        if not args.symbols_path:
            print("Error: --symbols-path is required when not running tests")
            parser.print_help()
            sys.exit(1)
        start_server(args.symbols_path, args.port)
