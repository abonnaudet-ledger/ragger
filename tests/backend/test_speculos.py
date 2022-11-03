from unittest import TestCase
from unittest.mock import patch
from pathlib import Path
from typing import Optional

from ragger import Firmware, RAPDU, ExceptionRAPDU
from ragger.backend import SpeculosBackend
from ragger.backend import RaisePolicy
from ragger.backend import NavigationInstruction

from tests.stubs import SpeculosServerStub, EndPoint, APDUStatus

ROOT_SCREENSHOT_PATH = Path(__file__).parent.parent.resolve()


class TestbackendSpeculos(TestCase):
    """
    Test patterns explained:

    ```
    def test_something(self):
        # patches 'subprocess' so that Speculos Client won't actually launch an app inside Speculos
        with patch("speculos.client.subprocess"):
            # starts the Speculos server stub, which will answer the SpeculosClient requests
            with SpeculosServerStub():
                # starts the backend: starts the underlying SpeculosClient so that exchanges can be
                # performed
                with self.backend:
    ```

    Sent APDUs:

    - starting with '00' means the response has a APDUStatus.SUCCESS status (0x9000)
    - else means the response has a APDUStatus.ERROR status (arbitrarily set to 0x8000)
    """

    def setUp(self):
        self.firmware = Firmware('nanos', '2.1')
        self.backend = SpeculosBackend("some app", self.firmware)

    def check_rapdu(self, rapdu: RAPDU, expected: Optional[bytes] = None, status: int = 0x9000):
        self.assertEqual(rapdu.status, status)
        if expected is None:
            return
        self.assertEqual(rapdu.data, expected)

    def test___init__ok(self):
        SpeculosBackend("some app", firmware=self.firmware)

    def test___init__args_ok(self):
        SpeculosBackend("some app", firmware=self.firmware, args=["some", "specific", "arguments"])

    def test___init__args_nok(self):
        with self.assertRaises(AssertionError):
            SpeculosBackend("some app", firmware=self.firmware, args="not a list")

    def test_exchange_raw(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    rapdu = self.backend.exchange_raw(bytes.fromhex("00000000"))
                    self.check_rapdu(rapdu, expected=bytes.fromhex(EndPoint.APDU))

    def test_exchange_raw_error(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    self.backend.raise_policy = RaisePolicy.RAISE_NOTHING
                    rapdu = self.backend.exchange_raw(bytes.fromhex("01000000"))
                    self.check_rapdu(rapdu,
                                     expected=bytes.fromhex(EndPoint.APDU),
                                     status=APDUStatus.ERROR)

    def test_exchange_raw_raises(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    with self.assertRaises(ExceptionRAPDU) as error:
                        self.backend.exchange_raw(bytes.fromhex("01000000"))
                    self.assertEqual(error.exception.status, APDUStatus.ERROR)

    def test_exchange_raw_raise_valid(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    self.backend.raise_policy = RaisePolicy.RAISE_ALL
                    with self.assertRaises(ExceptionRAPDU) as error:
                        self.backend.exchange_raw(bytes.fromhex("00000000"))
                    self.assertEqual(error.exception.status, APDUStatus.SUCCESS)

    def test_send_raw(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    self.assertIsNone(self.backend._pending)
                    self.backend.send_raw(bytes.fromhex("00000000"))
                    self.assertIsNotNone(self.backend._pending)

    def test_receive_error(self):
        with self.assertRaises(AssertionError):
            self.backend.receive()

    def test_receive_ok(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    self.backend.send_raw(bytes.fromhex("00000000"))
                    rapdu = self.backend.receive()
                    self.check_rapdu(rapdu, expected=bytes.fromhex(EndPoint.APDU))

    def test_exchange_async_raw_ok(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    with self.backend.exchange_async_raw(bytes.fromhex("00000000")):
                        self.assertIsNone(self.backend.last_async_response)
                    rapdu = self.backend.last_async_response
                    self.assertIsNotNone(rapdu)
                    self.check_rapdu(rapdu, expected=bytes.fromhex(EndPoint.APDU))

    def test_exchange_async_raw_error(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    self.backend.raise_policy = RaisePolicy.RAISE_NOTHING
                    with self.backend.exchange_async_raw(bytes.fromhex("01000000")):
                        self.assertIsNone(self.backend.last_async_response)
                    rapdu = self.backend.last_async_response
                    self.assertIsNotNone(rapdu)
                    self.check_rapdu(rapdu,
                                     expected=bytes.fromhex(EndPoint.APDU),
                                     status=APDUStatus.ERROR)

    def test_exchange_async_raw_raises(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    with self.assertRaises(ExceptionRAPDU) as error:
                        with self.backend.exchange_async_raw(bytes.fromhex("01000000")):
                            pass
                    self.assertEqual(error.exception.status, APDUStatus.ERROR)

    def test_exchange_async_raw_raise_valid(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    self.backend.raise_policy = RaisePolicy.RAISE_ALL
                    with self.assertRaises(ExceptionRAPDU) as error:
                        with self.backend.exchange_async_raw(bytes.fromhex("00000000")):
                            pass
                    self.assertEqual(error.exception.status, APDUStatus.SUCCESS)

    def test_clicks(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    self.backend.right_click()
                    self.backend.left_click()
                    self.backend.both_click()

    def test_navigate_until_snap(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    ret = self.backend.navigate_until_snap(ROOT_SCREENSHOT_PATH, "generic", 0, 2)
                self.assertEqual(ret, 2)

    def test_navigate_and_compare_until_snap(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    ret = self.backend.navigate_and_compare_until_snap(
                        ROOT_SCREENSHOT_PATH, "generic", 0, 2)
                self.assertTrue(ret)

    def test_navigate_fail_after_last_action(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    with self.assertRaises(ValueError) as error:
                        self.backend.navigate_and_compare_until_snap(ROOT_SCREENSHOT_PATH,
                                                                     "generic", 0, 1)
                    self.assertIn("Timeout waiting for screen change", str(error.exception))

    def test_navigate_fail_cannot_find_first_snap(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    with self.assertRaises(ValueError) as error:
                        self.backend.navigate_until_snap(ROOT_SCREENSHOT_PATH, "generic", 3, 2)
                    self.assertIn("Could not find first snapshot", str(error.exception))

    def test_navigate_fail_cannot_find_last_snap(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    with self.assertRaises(ValueError) as error:
                        self.backend.navigate_until_snap(ROOT_SCREENSHOT_PATH, "generic", 0, 4)
                    self.assertIn("Timeout waiting for snap", str(error.exception))

    def test_navigate_and_compare(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    instructions = [
                        NavigationInstruction.GO_TO_NEXT_SCREEN,
                        NavigationInstruction.GO_TO_NEXT_SCREEN,
                        NavigationInstruction.GO_TO_PREVIOUS_SCREEN,
                        NavigationInstruction.GO_TO_NEXT_SCREEN, NavigationInstruction.CONFIRM,
                        NavigationInstruction.GO_TO_NEXT_SCREEN, NavigationInstruction.CONFIRM
                    ]
                    ret = self.backend.navigate_and_compare(ROOT_SCREENSHOT_PATH,
                                                            "test_navigate_and_compare",
                                                            instructions)
                self.assertTrue(ret)

    def test_navigate_and_compare_no_golden(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    instructions = [NavigationInstruction.GO_TO_NEXT_SCREEN]
                    with self.assertRaises(FileNotFoundError) as error:
                        self.backend.navigate_and_compare(ROOT_SCREENSHOT_PATH,
                                                          "test_navigate_and_compare_no_golden",
                                                          instructions)
                    self.assertIn("No such file or directory", str(error.exception))
                    self.assertIn("test_navigate_and_compare_no_golden/00001.png",
                                  str(error.exception))

    def test_navigate_and_compare_wrong_golden(self):
        with patch("speculos.client.subprocess"):
            with SpeculosServerStub():
                with self.backend:
                    instructions = [NavigationInstruction.GO_TO_NEXT_SCREEN]
                    with self.assertRaises(ValueError) as error:
                        self.backend.navigate_and_compare(ROOT_SCREENSHOT_PATH,
                                                          "test_navigate_and_compare_wrong_golden",
                                                          instructions)
                    self.assertIn("Screenshots", str(error.exception))
                    self.assertIn("00001.png does not match golden", str(error.exception))
