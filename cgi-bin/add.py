#!python

import imp
import collections
import json
import tempfile
import shutil
import traceback
import zipfile
import subprocess
from uuid import uuid4
from os import path
from os.path import join
from cgi import FieldStorage

symbols_server_common = imp.load_source('symbols_server_common', 'symbols_server_common.py')
from symbols_server_common import *


fields_tuple = collections.namedtuple(
    "fields_tuple",
    "zip_content, file_name, product_name product_version comment")


def get_str_value(form, field_name):
    value = form.getvalue(field_name)
    if value is None:
        return ""
    else:
        return str(value)


def extract_fields():
    form = FieldStorage()
    if Fields.zip in form.keys():
        file_item = form[Fields.zip]
        if file_item.filename:
            if file_item.done == -1:
                raise Exception("File not fully downloaded.")
            else:
                product_name = get_str_value(form, Fields.product_name)
                product_version = get_str_value(form, Fields.product_version)
                comment = get_str_value(form, Fields.comment)
                zip_content = form.getvalue(Fields.zip)
                return fields_tuple(zip_content, file_item.filename, product_name, product_version, comment)
        else:
            raise Exception(Fields.zip + " field is not a file")
    else:
        raise Exception("No " + Fields.zip + " field")


def unzip(zip_path, tmp_dir):
    output_dir = join(tmp_dir, str(uuid4()))
    with zipfile.ZipFile(zip_path, "r") as zip_file:
        zip_file.extractall(output_dir)
    return output_dir


def add_symbols(dir_path, fields):
    comment = fields.comment
    if comment == "":
        comment = fields.file_name
    args = [Env.get_symstore_path(), "add",
            "/compress",
            "/r", "/f", dir_path,
            "/s", Env.get_symbol_repo_path(),
            "/t", fields.product_name,
            "/v", fields.product_version,
            "/c", comment]
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.wait() != 0:
        raise Exception(
            "Command: " + " ".join(args)
            + " -- Output: " + stdout.decode()
            + " -- Errors:" + stderr.decode())


def save_file(zip_content, file_name, tmp_dir):
    output_file_path = join(tmp_dir, file_name)
    with open(output_file_path, 'wb') as output_file:
        output_file.write(zip_content)
    if path.getsize(output_file_path) == 0:
        raise Exception("File is empty")
    else:
        return output_file_path


def handle_fields(fields):
    tmp_dir = join(tempfile.gettempdir(), "symbols_server_" + str(uuid4()))
    os.mkdir(tmp_dir)
    try:
        zip_path = save_file(fields.zip_content, fields.file_name, tmp_dir)
        unzip_dir_path = unzip(zip_path, tmp_dir)
        add_symbols(unzip_dir_path, fields)
    finally:
        shutil.rmtree(tmp_dir)


def print_json(status, message=""):
    print(json.dumps({"status": status, "message": message}))


print("Content-Type: application/json")
print("")
try:
    handle_fields(extract_fields())
    print_json("success")
except Exception as e:
    print_json("error", str(e) + " -- " + traceback.format_exc())
