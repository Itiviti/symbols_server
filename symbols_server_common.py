import os

symbolsRepoPathEnvVar = 'SYMBOLS_REPO_PATH'
symstorePathEnvVar = 'SYMBOLS_SYMSTORE_PATH'


class Env:
    def __init__(self):
        pass

    @staticmethod
    def get_symbol_repo_path():
        return os.environ[symbolsRepoPathEnvVar]

    @staticmethod
    def set_symbols_repo_path(repo_path):
        os.environ[symbolsRepoPathEnvVar] = repo_path

    @staticmethod
    def get_symstore_path():
        return os.environ[symstorePathEnvVar]

    @staticmethod
    def set_symstore_path(symstore_path):
        os.environ[symstorePathEnvVar] = symstore_path


class Fields:
    zip = 'zip'
    product_name = 'product_name'
    product_version = 'product_version'
    comment = 'comment'

    def __init__(self):
        pass
