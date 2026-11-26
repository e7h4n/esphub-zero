# EspHub Wi-Fi for Cardputer Zero

A keyboard-driven GUI for provisioning EspHub devices over Bluetooth.

On a Debian 13 Cardputer Zero, build and install the launcher app:

```sh
./package.sh /tmp/esphub-wifi.deb
sudo apt install /tmp/esphub-wifi.deb
```

Open **EspHub Wi-Fi** in APPLaunch. Choose **Sign in**, scan the QR on a phone
(or visit `accounts.esphub.ai/device` and enter the code), and approve EspHub
device access. The public Clerk client uses the device grant with
`devices:read devices:write offline_access`. Sign out removes the local grant.

1. Put the target in EspHub Bootloader and choose **Nearby devices**. The Zero
   turns on its Bluetooth adapter if needed and scans. When signed in, a matching
   advertisement shows the registered device name and signal strength. Other
   advertisements show their Bluetooth address.
2. Select a board. The app automatically selects a registration when exactly
   one of your physical devices has that Bluetooth address. If the address is
   missing or ambiguous, choose a registration manually. The TLS-PSK handshake
   verifies the board before Wi-Fi setup.
3. Select **Scan networks** to scan on the target or **Enter SSID manually**
   for a hidden network. Enter the network password (empty for an open network).
4. **Wi-Fi saved** appears after the target reports that it saved and connected
   to the selected SSID. If the link is lost after submission, check the device
   before retrying. The app never automatically replays a join.

Use the arrow keys and Enter. Esc goes back, Ctrl+Q exits. If the app turned
Bluetooth on, choose **Turn off and exit** or **Keep on and exit**. Esc at this
prompt returns to the main menu. Bluetooth that was already on stays on.
Start via APPLaunch so the launcher releases the physical keyboard and LCD. The Wi-Fi password
and BLE credential are held in memory only. The OAuth grant is stored under
`~/.local/share/esphub-wifi/` with a user-only file mode.

Originally merged in [EspHub PR #39](https://github.com/okou-ai/esphub/pull/39).
