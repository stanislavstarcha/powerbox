import _ from "lodash";

import { Loading, QSpinnerGears } from "quasar";
import { acceptHMRUpdate, defineStore } from "pinia";
import { Preferences } from "@capacitor/preferences";
import { numbersToDataView } from "@capacitor-community/bluetooth-le";

import { useRouter } from "vue-router";
import { useATSStore } from "stores/ats";
import { useBMSStore } from "stores/bms";
import { usePSUStore } from "stores/psu";
import { useInverterStore } from "stores/inverter";
import { useMCUStore } from "stores/mcu";
import { useHistoryStore } from "stores/history";

import { i18n } from "src/boot/i18n";

import {
    BLE_CORE_SERVICE_UUID,
    BLE_BMS_STATE_UUID,
    BLE_PSU_STATE_UUID,
    BLE_MCU_STATE_UUID,
    BLE_OTA_STATE_UUID,
    BLE_INVERTER_STATE_UUID,
    BLE_ATS_STATE_UUID,
    BLE_HISTORY_STATE_UUID,
    BLE_RUN_COMMAND_UUID,
    COMMAND_PULL_HISTORY,
    COMMAND_PSU_CURRENT,
    COMMAND_ATS_ENABLE,
    COMMAND_ATS_DISABLE,
} from "stores/uuids";
import { dataViewToHexDump } from "src/utils/index.js";

const DEFAULT_LANGUAGE = "uk";

let BleClient;
async function loadBluetoothModule() {
    if (process.env.NODE_ENV === "production" || true) {
        const bleModule = await import("@capacitor-community/bluetooth-le");
        BleClient = bleModule.BleClient;
        console.log("Loaded Bluetooth Module", BleClient);
    } else {
        BleClient = await import("./mock");
        console.log("Loaded Bluetooth Mock Client");
    }
}

export const useAppStore = defineStore("app", {
    state: () => ({
        initialised: false,
        scanning: false,
        connecting: false,
        deviceId: null,
        devices: [],

        ats: false,
        currentLimit: 0,
        language: i18n.global.locale,
    }),

    actions: {
        async bootstrap() {
            this.atsStore = useATSStore();
            this.bmsStore = useBMSStore();
            this.inverterStore = useInverterStore();
            this.mcuStore = useMCUStore();
            this.psuStore = usePSUStore();
            this.historyStore = useHistoryStore();

            await loadBluetoothModule();
            await BleClient.initialize();
            await this.historyStore.initialise();
            await this.loadAppPreferences();
        },

        async scan() {
            this.scanning = true;
            Loading.show({
                message: "searchingForDevices",
                spinner: QSpinnerGears,
            });
            this.clearDevices();

            return new Promise((resolve, reject) => {
                try {
                    console.log("Requesting BLE scan", BLE_CORE_SERVICE_UUID);
                    BleClient.requestLEScan(
                        { services: [BLE_CORE_SERVICE_UUID] },
                        (result) => {
                            this.addDevice(result.device);
                        },
                    );

                    setTimeout(async () => {
                        this.scanning = false;
                        Loading.hide();
                        try {
                            await BleClient.stopLEScan();
                            resolve();
                        } catch (error) {
                            reject();
                        }
                    }, 1000);
                } catch (error) {
                    console.error("Scan failed:", error);
                    reject();
                }
            });
        },

        clearDevices() {
            this.devices = [];
            this.deviceId = null;
        },

        async connect(deviceId) {
            try {
                Loading.show({
                    message: "connectingToDevice",
                    spinner: QSpinnerGears,
                });
                console.log("Connecting to device", deviceId);

                this.deviceId = deviceId;
                this.bmsStore.initialiseChartData();
                this.psuStore.initialiseChartData();
                this.inverterStore.initialiseChartData();
                console.log("Initialised controllers data");

                await BleClient.connect(deviceId, (deviceId) => {
                    this.onDisconnect(deviceId);
                });

                await this.loadDevicePreferences();

                const [
                    atsState,
                    bmsState,
                    psuState,
                    inverterState,
                    mcuState,
                    otaState,
                ] = await Promise.all([
                    BleClient.read(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_ATS_STATE_UUID,
                    ),
                    BleClient.read(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_BMS_STATE_UUID,
                    ),
                    BleClient.read(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_PSU_STATE_UUID,
                    ),
                    BleClient.read(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_INVERTER_STATE_UUID,
                    ),
                    BleClient.read(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_MCU_STATE_UUID,
                    ),
                    BleClient.read(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_OTA_STATE_UUID,
                    ),
                ]);

                await Promise.all([
                    BleClient.startNotifications(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_ATS_STATE_UUID,
                        this.atsStore.parseState,
                    ),

                    BleClient.startNotifications(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_BMS_STATE_UUID,
                        this.bmsStore.parseState,
                    ),

                    BleClient.startNotifications(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_PSU_STATE_UUID,
                        this.psuStore.parseState,
                    ),

                    BleClient.startNotifications(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_INVERTER_STATE_UUID,
                        this.inverterStore.parseState,
                    ),

                    BleClient.startNotifications(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_MCU_STATE_UUID,
                        this.mcuStore.parseState,
                    ),

                    BleClient.startNotifications(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_OTA_STATE_UUID,
                        this.mcuStore.parseOTAState,
                    ),

                    BleClient.startNotifications(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_HISTORY_STATE_UUID,
                        this.historyStore.parseState,
                    ),

                    BleClient.startNotifications(
                        deviceId,
                        BLE_CORE_SERVICE_UUID,
                        BLE_ATS_STATE_UUID,
                        this.atsStore.parseState,
                    ),
                ]);

                // request history
                await this.runBLECommand(
                    numbersToDataView([COMMAND_PULL_HISTORY]),
                );

                this.atsStore.parseState(atsState);
                this.bmsStore.parseState(bmsState);
                this.psuStore.parseState(psuState);
                this.inverterStore.parseState(inverterState);
                this.mcuStore.parseState(mcuState);
                this.mcuStore.checkFirmwareUpdate();

                console.log("Connected to device:", deviceId);
                Loading.hide();
            } catch (error) {
                console.error(
                    "Connection failed:",
                    error.name,
                    error.message,
                    error.stack,
                );
                Loading.hide();
                return false;
            }
        },

        async runBLECommand(view) {
            console.log(
                "Run BLE command:",
                BleClient,
                this.deviceId,
                dataViewToHexDump(view),
            );
            await BleClient.write(
                this.deviceId,
                BLE_CORE_SERVICE_UUID,
                BLE_RUN_COMMAND_UUID,
                view,
            );
        },

        async disconnect() {
            await BleClient.disconnect(this.deviceId);
        },

        onDisconnect(deviceId) {
            console.log("Disconnected from device", deviceId);
            this.deviceId = null;
            this.devices = [];
            this.router.push({ name: "Discover" });
        },

        async loadAppPreferences() {
            const value = await Preferences.get({ key: "language" });
            this.setLanguage(
                _.defaultTo(JSON.parse(value.value), DEFAULT_LANGUAGE),
            );
        },

        async loadDevicePreferences() {
            const ats = await Preferences.get({ key: "ats" });
            const current = await Preferences.get({ key: "current" });
            this.setATS(_.defaultTo(JSON.parse(ats.value), false));
            this.setCurrentLimit(_.defaultTo(JSON.parse(current.value), 0));
        },

        async getPreference(key) {
            const v = await Preferences.get({ key });
            return JSON.parse(v.value);
        },

        async savePreference(key, value) {
            console.log("storing preference", key, value);
            await Preferences.set({
                key: key,
                value: JSON.stringify(value),
            });
        },

        setATS(value) {
            this.savePreference("ats", value).then(() => {
                this.ats = value;
                if (value) {
                    this.runBLECommand(numbersToDataView([COMMAND_ATS_ENABLE]));
                } else {
                    this.runBLECommand(
                        numbersToDataView([COMMAND_ATS_DISABLE]),
                    );
                }
            });
        },

        setLanguage(language) {
            console.log("set language", language);
            this.savePreference("language", language).then(() => {
                this.language = language;
                i18n.global.locale = language;
            });
        },

        setCurrentLimit(value) {
            this.savePreference("current", value).then(() => {
                this.currentLimit = value;
                this.runBLECommand(
                    numbersToDataView([COMMAND_PSU_CURRENT, value]),
                );
            });
        },

        addDevice(device) {
            this.devices.push(device);
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useAppStore, import.meta.hot));
}
