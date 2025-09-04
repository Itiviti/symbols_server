# Symbols Server
Provide http server for symbols (PDBs) and a way to manage them

Currently, it is making available symbols through the (mandatory) directory sent as parameter when starting the app.
We can add new symbols using _/cgi-bin/add.py_. There is an example how to use it in _index.html_.

It can be used together with this [gradle plugin](https://github.com/reeflog/gradle-symstoreserver-plugin) for continuous integration.

The server is doing an itegration test at startup.

## To do:
- remove symbols
- list symbols (but already accessible through _/symbols/000Admin/server.txt_, symstore format)

## Microsoft documentation around symstore tool

[SymStore Command-Line Options](https://msdn.microsoft.com/fr-fr/library/windows/desktop/ms681378(v=vs.85).aspx) - Full command line documentation

[Using SymStore](https://msdn.microsoft.com/en-us/library/windows/desktop/ms681417(v=vs.85).aspx) - Examples and other information about the usage of Symstore.exe

[Windows SDK for Windows 8.1](https://developer.microsoft.com/en-us/windows/downloads/windows-8-1-sdk) - Page to download the SDK
