"""Bluetooth power and exit decisions in the Cardputer app."""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, call, patch

import dbus

from app import App
from hub import Problem
from screen import Back, Quit, Screen


async def wait_for_action(title, rows, action):
    return await action


class BluetoothTests(unittest.IsolatedAsyncioTestCase):
    async def test_scan_and_exit_choices(self):
        # Scan again, leave discovery, then choose Exit and restore power.
        # Ctrl+Q in discovery goes directly to the same choice.
        for initially_on, choices, writes in [
            (False, [0, 0, Back(), 2, 0], [True, False]),
            (False, [0, Quit(), 1], [True]),
            (False, [0, Back(), Back(), Back(), 2, 1], [True]),
            (True, [0, Quit()], []),
            (False, [2], []),
        ]:
            with self.subTest(initially_on=initially_on, choices=choices):
                state = initially_on
                props = Mock()
                props.Get.side_effect = lambda *args, **kwargs: state

                def set_power(interface, name, value, **kwargs):
                    nonlocal state
                    state = bool(value)

                props.Set.side_effect = set_power

                async def scan():
                    self.assertTrue(state)
                    return []

                ui = Mock(
                    wait=wait_for_action, menu=AsyncMock(side_effect=choices),
                    message=AsyncMock(),
                )
                with (
                    patch("app.dbus.SystemBus"),
                    patch("app.dbus.Interface", return_value=props),
                    patch("app.nearby", scan),
                ):
                    await App(ui, Mock(tokens={})).run()
                self.assertEqual([bool(c.args[2]) for c in props.Set.call_args_list], writes)
                self.assertEqual(state, writes[-1] if writes else initially_on)
                if not writes:
                    self.assertNotIn("Turn Bluetooth off?", [c.args[0] for c in ui.menu.await_args_list])
                if choices == [2]:
                    props.Get.assert_not_called()

    async def test_quit_queued_while_powering_on(self):
        ui = Screen(lambda image: None)
        for key in ("ENTER", "QUIT", "ENTER"):
            ui.keys.put_nowait(key)

        async def pending_scan():
            await asyncio.Future()

        with (
            patch("app.set_bluetooth_power", return_value=True) as power,
            patch("app.nearby", pending_scan),
        ):
            await asyncio.wait_for(App(ui, Mock(tokens={})).run(), 3)
        self.assertEqual(power.call_args_list, [call(True), call(False)])

    async def test_power_on_denied_does_not_start_scan(self):
        props = Mock()
        props.Get.return_value = False
        props.Set.side_effect = dbus.DBusException("denied")
        ui = Mock(menu=AsyncMock(side_effect=[0, 2]), message=AsyncMock())
        with (
            patch("app.dbus.SystemBus"),
            patch("app.dbus.Interface", return_value=props),
            patch("app.nearby") as scan,
        ):
            await App(ui, Mock(tokens={})).run()
        self.assertIn("turn Bluetooth on", ui.message.await_args.args[1])
        scan.assert_not_called()

    async def test_failed_power_off_offers_exit_choice_again(self):
        ui = Mock(
            wait=wait_for_action,
            menu=AsyncMock(side_effect=[0, Quit(), 0, 1]),
            message=AsyncMock(),
        )
        error = Problem("Could not turn Bluetooth off.")
        with (
            patch("app.set_bluetooth_power", side_effect=[True, error]) as power,
            patch("app.nearby", return_value=[]),
        ):
            await App(ui, Mock(tokens={})).run()
        ui.message.assert_awaited_with("Bluetooth", str(error))
        self.assertEqual(power.call_args_list, [call(True), call(False)])
        self.assertEqual(ui.menu.await_args.args[1], ["Turn off and exit", "Keep on and exit"])
