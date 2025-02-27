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
__version__ = "0.6.0"

import logging

from ragger.error import ExceptionRAPDU
from ragger.firmware import Firmware, SDK_VERSIONS
from ragger.utils import RAPDU, Crop

logger = logging.getLogger(__package__)
logger.setLevel(level=logging.DEBUG)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s] %(name)s - %(message)s'))

logger.addHandler(handler)

__all__ = ["Crop", "ExceptionRAPDU", "Firmware", "logger", "RAPDU", "SDK_VERSIONS"]
