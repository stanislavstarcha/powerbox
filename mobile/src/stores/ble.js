import { acceptHMRUpdate, defineStore } from "pinia";
import {
    BleClient,
    numbersToDataView,
    dataViewToNumbers,
} from "@capacitor-community/bluetooth-le";

import { Loading, QSpinnerGears } from "quasar";

import { useRouter } from "vue-router";
import { useBMSStore } from "stores/bms";
import { usePSUStore } from "stores/psu";
import { useInverterStore } from "stores/inverter";
import { useESPStore } from "stores/esp";
import { useHistoryStore } from "stores/history";

import {
    coreServiceUUID,
    bmsUUID,
    psuUUID,
    espUUID,
    inverterUUID,
    historyUUID,
    commandUUID,
} from "stores/uuids";

const bmsStore = useBMSStore();
const espStore = useESPStore();
const psuStore = usePSUStore();
const inverterStore = useInverterStore();
const historyStore = useHistoryStore();

async function loadBluetoothModule() {
    if (process.env.NODE_ENV === "production" || true) {
        console.log("Loaded Bluetooth Module", BleClient);
    } else {
        BleClient = await import("./mock");
        console.log("Loaded Bluetooth Mock Client");
    }
}

export const useBLEStore = defineStore("ble", {
    router: useRouter(),

    state: () => ({
        connected: false,
        scanning: false,
        connecting: false,
        deviceId: null,
        devices: [],
    }),

    actions: {
        async bootstrap() {
            await loadBluetoothModule();
            await BleClient.initialize();
        },

        async scan() {
            this.scanning = true;
            Loading.show({
                message: "Шукаємо пристрої...",
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

        addDevice(device) {
            this.devices.push(device);
        },

        clearDevices() {
            this.devices = [];
            this.deviceId = null;
        },

        async connect(deviceId) {
            try {
                Loading.show({
                    message: "Зʼєднуємось зі станцієй...",
                    spinner: QSpinnerGears,
                });
                this.deviceId = deviceId;
                bmsStore.initialiseChartData();
                psuStore.initialiseChartData();
                inverterStore.initialiseChartData();

                await BleClient.connect(deviceId, (deviceId) => {
                    this.connected = false;
                    this.deviceId = null;
                    this.devices = [];

                    this.router.push({ name: "Discover" });
                });

                const [bmsState, psuState, inverterState, espState] =
                    await Promise.all([
                        BleClient.read(deviceId, coreServiceUUID, bmsUUID),
                        BleClient.read(deviceId, coreServiceUUID, psuUUID),
                        BleClient.read(deviceId, coreServiceUUID, inverterUUID),
                        BleClient.read(deviceId, coreServiceUUID, espUUID),
                    ]);

                await Promise.all([
                    BleClient.startNotifications(
                        deviceId,
                        coreServiceUUID,
                        bmsUUID,
                        bmsStore.parseState,
                    ),
                    // BleClient.startNotifications(
                    //     deviceId,
                    //     coreServiceUUID,
                    //     psuUUID,
                    //     psuStore.parseState,
                    // ),
                    //
                    // BleClient.startNotifications(
                    //     deviceId,
                    //     coreServiceUUID,
                    //     inverterUUID,
                    //     inverterStore.parseState,
                    // ),
                    //
                    // BleClient.startNotifications(
                    //     deviceId,
                    //     coreServiceUUID,
                    //     espUUID,
                    //     espStore.parseState,
                    // ),

                    BleClient.startNotifications(
                        deviceId,
                        coreServiceUUID,
                        historyUUID,
                        historyStore.parseState,
                    ),
                ]);

                // request history
                await this.writeState(commandUUID, 0x01);

                bmsStore.parseState(bmsState);
                psuStore.parseState(psuState);
                inverterStore.parseState(inverterState);
                espStore.parseState(espState);

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
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useBLEStore, import.meta.hot));
}
