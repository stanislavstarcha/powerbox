# powerbox (powerbox)

The following steps describe first time installation of Capacitor.

Add capacitor
```
cd ./mobile
quasar mode add capacitor
```

Add the following dependencies to `src-capacitor/package.json`

```
{
    "@capacitor-community/bluetooth-le": "^7.0.0",
    "@capacitor/android": "^7.1.0",
    "@capacitor/app": "^7.0.0",
    "@capacitor/cli": "^7.1.0",
    "@capacitor/core": "^7.1.0",
    "@capacitor/ios": "^7.1.0",
    "@capacitor/preferences": "^7.0.0",
    "@capawesome-team/capacitor-wifi": "^7.0.1"
}
```

```
cd src-capacitor
yarn install
```

### IOS

App -> Signing & Capabilities and select the team.

Open `scr-capacitor/ios/App/App/Info.plist` and add the following scopes

```
	<key>NSBluetoothAlwaysUsageDescription</key>
	<string>We need access to Bluetooth to connect with devices</string>
	<key>NSBluetoothPeripheralUsageDescription</key>
	<string>We need Bluetooth for peripheral device communication</string>

    <key>NSLocationWhenInUseUsageDescription</key>
    <string>We need your location to request Wi-Fi information.</string>
    <key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
    <string>We need your location to request Wi-Fi information.</string>

	<key>UISupportedInterfaceOrientations</key>
	<array>
		<string>UIInterfaceOrientationPortrait</string>
	</array>

```
