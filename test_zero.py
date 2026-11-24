"""Regression checks for the GUI's provisioning decisions (no radio required)."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

from app import App, JoinFailed, join, networks
from hub import Problem
from screen import Screen


class ProvisionTests(unittest.IsolatedAsyncioTestCase):
    async def test_registration_selection(self):
        address = "02:AA:BB:CC:DD:EE"
        board = {"kind": "physical", "id": "one", "name": "Kitchen", "ble_address": address.lower()}
        other = {"kind": "physical", "id": "two", "name": "Desk"}

        async def wait(title, rows, action):
            return await action

        for devices, manual in [
            ([board, other], False),
            ([dict(board, ble_address=None), other], True),
            ([board, dict(other, ble_address=address)], True),
        ]:
            with self.subTest(devices=devices):
                ui = Mock(wait=wait, menu=AsyncMock(return_value=1))
                hub = Mock(tokens={"signed": True})
                hub.tool = AsyncMock(side_effect=[devices, Problem("test credential request")])
                with self.assertRaisesRegex(Problem, "test credential request"):
                    await App(ui, hub).configure(Mock(address=address))
                hub.tool.assert_awaited_with("wifi.ble_credential", device_id="two" if manual else "one")
                self.assertEqual(ui.menu.await_count, int(manual))

    async def test_named_and_unmatched_advertisements(self):
        async def wait(title, rows, action):
            return await action
        ui = Mock(wait=wait, menu=AsyncMock(return_value=1))
        app = App(ui, Mock(tokens={"signed": True}))
        app.registrations = AsyncMock(return_value=[{"name": "Kitchen", "ble_address": "02:aa:bb:cc:dd:ee"}])
        app.configure = AsyncMock()
        other = Mock(address="02:11:22:33:44:55")
        pairs = [(Mock(address="02:AA:BB:CC:DD:EE"), Mock(rssi=-40)), (other, Mock(rssi=-65))]
        with patch("app.nearby", new=AsyncMock(return_value=pairs)):
            await app.discover()
        self.assertEqual(ui.menu.await_args.args[1], ["Kitchen    -40 dBm", "02:11:22:33:44:55    -65 dBm", "Scan again"])
        app.configure.assert_awaited_once_with(other, app.registrations.return_value)

    async def test_selected_wifi_and_manual_hidden(self):
        for manual in (False, True):
            with self.subTest(manual=manual):
                ui = Mock()

                async def wait(title, rows, action):
                    return await action

                ui.wait = wait
                ui.menu = AsyncMock(side_effect=[1] if manual else [0, 0])
                ui.entry = AsyncMock(side_effect=["lab", ""] if manual else ["test-pw"])
                ui.message = AsyncMock()
                board = Mock()
                board.request = AsyncMock(
                    side_effect=(
                        ([] if manual else [{"ssids": ["lab"]}])
                        + [{"joining": True}, {"state": "saved", "connected": "lab"}]
                    )
                )
                await networks(ui, board)
                board.request.assert_any_await(
                    "wifi.join",
                    ssid="lab",
                    password="" if manual else "test-pw",
                    hidden=manual,
                )
                self.assertEqual(ui.message.await_args.args[0], "Wi-Fi saved")

    async def test_empty_scan_returns_to_manual_entry(self):
        ui = Mock()

        async def wait(title, rows, action):
            return await action

        ui.wait = wait
        ui.menu = AsyncMock(side_effect=[0, 1])
        ui.message = AsyncMock()
        ui.entry = AsyncMock(side_effect=["hidden", "password"])
        board = Mock()
        board.request = AsyncMock(
            side_effect=[
                {"ssids": []},
                {"joining": True},
                {"state": "saved", "connected": "hidden"},
            ]
        )
        await networks(ui, board)
        board.request.assert_any_await(
            "wifi.join", ssid="hidden", password="password", hidden=True
        )

    async def test_wrong_network_then_failure(self):
        board = Mock()
        board.request = AsyncMock(
            side_effect=[
                {"joining": True},
                {"state": "saved", "connected": "old"},
                {"state": "failed"},
            ]
        )
        with self.assertRaises(JoinFailed):
            await join(board, "new", "", True)

    async def test_no_join_replay_on_disconnect(self):
        board = Mock()
        board.request = AsyncMock(side_effect=OSError)
        with self.assertRaisesRegex(Problem, "not confirmed"):
            await join(board, "lab", "test", False)
        self.assertEqual(board.request.await_count, 1)

    async def test_password_entry_masks_and_edits(self):
        ui = Screen(lambda image: None)
        ui.draw = Mock()
        for key in ("A", "B", "BACKSPACE", "!", "ENTER"):
            ui.keys.put_nowait(key)
        self.assertEqual(await ui.entry("Password", "Lab", 64, masked=True), "A!")
        fields = [frame.args[1][-1] for frame in ui.draw.call_args_list]
        self.assertEqual(fields, ["▏", "•▏", "••▏", "•▏", "••▏"])
