"""
   Copyright 2022 Ledger SAS

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
from .interface import BackendInterface, RaisePolicy, NavigationInstruction


ERROR_MSG = "This backend needs {}. Please install this package (run `pip install " \
    "--extra-index-url https://test.pypi.org/simple/ ragger[{}]` or check this address: '{}')"

try:
    from .speculos import SpeculosBackend
except ImportError:

    def SpeculosBackend(*args, **kwargs):  # type: ignore
        raise ImportError(
            ERROR_MSG.format("Speculos", "speculos", "https://github.com/LedgerHQ/speculos/"))


try:
    from .ledgercomm import LedgerCommBackend
except ImportError:

    def LedgerCommBackend(*args, **kwargs):  # type: ignore
        raise ImportError(
            ERROR_MSG.format("LedgerComm", "ledgercomm", "https://github.com/LedgerHQ/ledgercomm/"))


try:
    from .ledgerwallet import LedgerWalletBackend
except ImportError:

    def LedgerWalletBackend(*args, **kwargs):  # type: ignore
        raise ImportError(
            ERROR_MSG.format("LedgerWallet", "ledgerwallet",
                             "https://github.com/LedgerHQ/ledgerctl/"))


__all__ = [
    "SpeculosBackend", "LedgerCommBackend", "LedgerWalletBackend", "BackendInterface",
    "RaisePolicy", "NavigationInstruction"
]
