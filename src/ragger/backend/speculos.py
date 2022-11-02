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
from pathlib import Path
from contextlib import contextmanager
from io import BytesIO
from time import time
from typing import Optional, Generator, List

from PIL import Image
from speculos.client import SpeculosClient, ApduResponse, ApduException, screenshot_equal

from ragger import logger
from ragger.error import ExceptionRAPDU
from ragger.firmware import Firmware
from ragger.utils import RAPDU, Crop
from .interface import BackendInterface, NavigationInstruction


def raise_policy_enforcer(function):

    def decoration(self: 'SpeculosBackend', *args, **kwargs) -> RAPDU:
        # Catch backend raise
        try:
            rapdu: RAPDU = function(self, *args, **kwargs)
        except ApduException as error:
            rapdu = RAPDU(error.sw, error.data)

        logger.debug("Receiving '%s'", rapdu)

        if self.is_raise_required(rapdu):
            raise ExceptionRAPDU(rapdu.status, rapdu.data)
        else:
            return rapdu

    return decoration


class SpeculosBackend(BackendInterface):

    _ARGS_KEY = 'args'

    def __init__(self,
                 application: Path,
                 firmware: Firmware,
                 host: str = "127.0.0.1",
                 port: int = 5000,
                 **kwargs):
        super().__init__(firmware)
        self._host = host
        self._port = port
        args = ["--model", firmware.device, "--sdk", firmware.version]
        if self._ARGS_KEY in kwargs:
            assert isinstance(kwargs[self._ARGS_KEY], list), \
                f"'{self._ARGS_KEY}' ({kwargs[self._ARGS_KEY]}) keyword " \
                "argument  must be a list of arguments"
            kwargs[self._ARGS_KEY].extend(args)
        else:
            kwargs[self._ARGS_KEY] = args
        self._client: SpeculosClient = SpeculosClient(app=str(application),
                                                      api_url=self.url,
                                                      **kwargs)
        self._pending: Optional[ApduResponse] = None

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def __enter__(self) -> "SpeculosBackend":
        logger.info(f"Starting {self.__class__.__name__} stream")
        self._client.__enter__()
        return self

    def __exit__(self, *args, **kwargs):
        self._client.__exit__(*args, **kwargs)

    def send_raw(self, data: bytes = b"") -> None:
        logger.debug("Sending '%s'", data.hex())
        self._pending = ApduResponse(self._client._apdu_exchange_nowait(data))

    @raise_policy_enforcer
    def receive(self) -> RAPDU:
        assert self._pending is not None
        result = RAPDU(0x9000, self._pending.receive())
        return result

    @raise_policy_enforcer
    def exchange_raw(self, data: bytes = b"") -> RAPDU:
        logger.debug("Sending '%s'", data.hex())
        return RAPDU(0x9000, self._client._apdu_exchange(data))

    @raise_policy_enforcer
    def _get_last_async_response(self, response) -> RAPDU:
        return RAPDU(0x9000, response.receive())

    @contextmanager
    def exchange_async_raw(self, data: bytes = b"") -> Generator[None, None, None]:
        with self._client.apdu_exchange_nowait(cla=data[0],
                                               ins=data[1],
                                               p1=data[2],
                                               p2=data[3],
                                               data=data[5:]) as response:
            yield
            self._last_async_response = self._get_last_async_response(response)

    def right_click(self) -> None:
        self._client.press_and_release("right")

    def left_click(self) -> None:
        self._client.press_and_release("left")

    def both_click(self) -> None:
        self._client.press_and_release("both")

    def _get_snaps_dir_path(self, path: Path, test_case_name: Path, is_golden: bool) -> Path:
        if is_golden:
            subdir = "snapshots"
        else:
            subdir = "snapshots-tmp"
        return path / subdir / self._firmware.device / test_case_name

    def _get_snap_path(self, path: Path, index: int) -> Path:
        return path / f"{str(index).zfill(5)}.png"

    def _save_snap(self, dir_path: Path, index: int):
        screenshot = self._client.get_screenshot()
        img = Image.open(BytesIO(screenshot))
        img.save(self._get_snap_path(dir_path, index))

    def _snap_equal_with_crop(self, path: Path, bytes: BytesIO, crop: Crop = None):
        if crop is not None:
            return screenshot_equal(f"{path}",
                                    bytes,
                                    left=crop.left,
                                    upper=crop.upper,
                                    right=crop.right,
                                    lower=crop.lower)
        else:
            return screenshot_equal(f"{path}", bytes)

    def _compare_snap_with_timeout(self, path: Path, timeout_s: float = 5.0, crop: Crop = None):
        start = time()
        now = start
        while not (now - start > timeout_s):
            screenshot = self._client.get_screenshot()
            if self._snap_equal_with_crop(path, BytesIO(screenshot), crop):
                return True
            now = time()
        return False

    def _compare_snaps(self, path: Path, test_case_name: Path, last_img_idx: int = 0) -> bool:

        snaps_golden_path = self._get_snaps_dir_path(path, test_case_name, True)
        snaps_tmp_path = self._get_snaps_dir_path(path, test_case_name, False)

        if not snaps_golden_path.is_dir():
            raise ValueError(f"Golden snapshots directory ({snaps_golden_path}) does not exist.")

        if not snaps_tmp_path.is_dir():
            raise ValueError(f"Temporary snapshots directory ({snaps_golden_path}) does not exist.")

        for i in range(0, last_img_idx + 1):
            golden = self._get_snap_path(snaps_golden_path, i)
            tmp = self._get_snap_path(snaps_tmp_path, i)
            if not screenshot_equal(str(golden), str(tmp)):
                raise ValueError(f"Screenshots {tmp} does not match golden.")
        return True

    def navigate_until_snap(self,
                            path: Path,
                            test_case_name: Path,
                            start_img_idx: int = 0,
                            last_img_idx: int = 0,
                            take_snaps: bool = True,
                            timeout: int = 30,
                            crop_first: Crop = None,
                            crop_last: Crop = None) -> int:

        snaps_golden_path = self._get_snaps_dir_path(path, test_case_name, True)
        snaps_tmp_path = self._get_snaps_dir_path(path, test_case_name, False)

        if not snaps_golden_path.is_dir():
            raise ValueError(f"Golden snapshots directory ({snaps_golden_path}) does not exist.")

        snaps_tmp_path.mkdir(parents=True, exist_ok=True)

        img_idx = start_img_idx
        first_golden_snap = self._get_snap_path(snaps_golden_path, img_idx)
        last_golden_snap = self._get_snap_path(snaps_golden_path, last_img_idx)
        # Check if the first snapshot is found before going in the navigation loop.
        # It saves time in non-nominal cases where the navigation flow does not start.
        if self._compare_snap_with_timeout(first_golden_snap, timeout_s=2, crop=crop_first):
            start = time()
            # Navigate until the last snapshot specified in argument is found.
            while not self._compare_snap_with_timeout(
                    last_golden_snap, timeout_s=0.5, crop=crop_last):
                now = time()
                # Global navigation loop timeout in case the snapshot is never found.
                if (now - start > timeout):
                    raise ValueError(f"Timeout waiting for snap {last_golden_snap}")

                # Take snapshots if required.
                if take_snaps:
                    self._save_snap(snaps_tmp_path, img_idx)

                # TODO : Allow custom actions
                # Go to the next screen.
                self.navigate([NavigationInstruction.GO_TO_NEXT_SCREEN])
                img_idx += 1

            # Take last snapshot if required.
            if take_snaps:
                self._save_snap(snaps_tmp_path, img_idx)

            # TODO : Allow custom actions
            # Validation action when last snapshot is found.
            self.navigate([NavigationInstruction.CONFIRM])

            # Make sure there is a screen update after the final action.
            start = time()
            last_screen_update_timeout = 2
            while self._compare_snap_with_timeout(last_golden_snap, timeout_s=0.5, crop=crop_last):
                now = time()
                if (now - start > last_screen_update_timeout):
                    raise ValueError(
                        f"Timeout waiting for screen change after last snapshot : {last_golden_snap}"
                    )
        else:
            raise ValueError(f"Could not find first snapshot {first_golden_snap}")
        return img_idx

    def navigate_and_compare_until_snap(self,
                                        path: Path,
                                        test_case_name: Path,
                                        start_img_idx: int = 0,
                                        last_img_idx: int = 0) -> bool:
        # First navigate to the last image and take snapshots of every screen in the flow.
        img_idx = self.navigate_until_snap(path, test_case_name, start_img_idx, last_img_idx, True)
        # Then compare all snapshots taken to golden images.
        return self._compare_snaps(path, test_case_name, img_idx)

    def navigate_and_compare(self, path: Path, test_case_name: Path,
                             instructions: List[NavigationInstruction]) -> bool:
        snaps_tmp_path = self._get_snaps_dir_path(path, test_case_name, False)
        snaps_tmp_path.mkdir(parents=True, exist_ok=True)

        # First navigate to the last step and take snapshots of every screen in the flow.
        for idx, instruction in enumerate(instructions):
            self._save_snap(snaps_tmp_path, idx)

            self.navigate([instruction])

        # Take last screen snapshot
        self._save_snap(snaps_tmp_path, len(instructions))

        # Then compare all snapshots taken to golden images.
        return self._compare_snaps(path, test_case_name, len(instructions))
