import _ from "lodash";

import { Loading, QSpinnerGears } from "quasar";
import { acceptHMRUpdate, defineStore } from "pinia";
import { Preferences } from "@capacitor/preferences";
import { numbersToDataView } from "@capacitor-community/bluetooth-le";

import { useRouter } from "vue-router";
import { useBMSStore } from "stores/bms";
import { usePSUStore } from "stores/psu";
import { useInverterStore } from "stores/inverter";
import { useESPStore } from "stores/esp";
import { useATSStore } from "stores/ats";
import { useHistoryStore } from "stores/history";

import { pack_bool } from "src/utils/ble.js";
import { i18n } from "src/boot/i18n";

import {
    coreServiceUUID,
    bmsUUID,
    psuUUID,
    espUUID,
    inverterUUID,
    atsUUID,
    historyUUID,
    setCommandUUID,
    setATSUUID,
    setCurrentUUID,
} from "stores/uuids";

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
            this.bmsStore = useBMSStore();
            this.espStore = useESPStore();
            this.psuStore = usePSUStore();
            this.inverterStore = useInverterStore();
            this.atsStore = useATSStore();
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
                    console.log("Requesting BLE scan", coreServiceUUID);
                    BleClient.requestLEScan(
                        { services: [coreServiceUUID] },
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

                this.deviceId = deviceId;
                this.bmsStore.initialiseChartData();
                this.psuStore.initialiseChartData();
                this.inverterStore.initialiseChartData();

                await BleClient.connect(deviceId, (deviceId) => {
                    this.deviceId = null;
                    this.devices = [];
                    const router = useRouter();
                    router.push({ name: "Discover" });
                });

                await this.loadDevicePreferences();

                const [bmsState, psuState, inverterState, espState, atsState] =
                    await Promise.all([
                        BleClient.read(deviceId, coreServiceUUID, bmsUUID),
                        BleClient.read(deviceId, coreServiceUUID, psuUUID),
                        BleClient.read(deviceId, coreServiceUUID, inverterUUID),
                        BleClient.read(deviceId, coreServiceUUID, espUUID),
                        BleClient.read(deviceId, coreServiceUUID, atsUUID),
                    ]);

                await Promise.all([
                    BleClient.startNotifications(
                        deviceId,
                        coreServiceUUID,
                        bmsUUID,
                        this.bmsStore.parseState,
                    ),
                    BleClient.startNotifications(
                        deviceId,
                        coreServiceUUID,
                        psuUUID,
                        this.psuStore.parseState,
                    ),

                    BleClient.startNotifications(
                        deviceId,
                        coreServiceUUID,
                        inverterUUID,
                        this.inverterStore.parseState,
                    ),

                    BleClient.startNotifications(
                        deviceId,
                        coreServiceUUID,
                        espUUID,
                        this.espStore.parseState,
                    ),

                    BleClient.startNotifications(
                        deviceId,
                        coreServiceUUID,
                        historyUUID,
                        this.historyStore.parseState,
                    ),

                    BleClient.startNotifications(
                        deviceId,
                        coreServiceUUID,
                        atsUUID,
                        this.atsStore.parseState,
                    ),
                ]);

                // request history
                await this.writeState(setCommandUUID, 0x01);

                this.bmsStore.parseState(bmsState);
                this.psuStore.parseState(psuState);
                this.inverterStore.parseState(inverterState);
                this.espStore.parseState(espState);
                this.atsStore.parseState(atsState);

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

        async writeState(stateUUID, data) {
            const view = numbersToDataView([data]);
            await BleClient.write(
                this.deviceId,
                coreServiceUUID,
                stateUUID,
                view,
            );
        },

        async disconnect(deviceId) {
            await BleClient.disconnect(deviceId);
            console.log("Disconnected from device", deviceId);
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

        async savePreference(key, value) {
            await Preferences.set({
                key: key,
                value: JSON.stringify(value),
            });
        },

        setATS(value) {
            this.savePreference("ats", value).then(() => {
                this.ats = value;
                this.writeState(setATSUUID, pack_bool(value));
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
                this.writeState(setCurrentUUID, value);
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
