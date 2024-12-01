import { acceptHMRUpdate, defineStore } from "pinia";
import {
    unpack,
    unpack_bool,
    unpack_voltage,
    pack_bool,
} from "src/utils/ble.js";

import {
    HISTORY_PSU_TEMPERATURE,
    HISTORY_PSU_VOLTAGE,
    setChargingUUID,
} from "stores/uuids.js";
import { useAppStore } from "stores/app.js";

export const usePSUStore = defineStore("psu", {
    state: () => ({
        active: null,
        currentLimit: null,
        voltage: null,
        temperature: null,
        externalErrors: null,
        internalErrors: null,
        chartData: {},
        chartMappings: {
            [HISTORY_PSU_VOLTAGE]: unpack_voltage,
            [HISTORY_PSU_TEMPERATURE]: unpack,
        },
    }),

    actions: {
        parseState(view) {
            let offset = 0;

            this.voltage = unpack_voltage(view.getUint16(offset));
            offset += 2;

            this.active = unpack_bool(view.getUint8(offset));
            offset += 1;

            this.currentLimit = unpack(view.getUint8(offset));
            offset += 1;

            this.temperature = unpack(view.getUint8(offset));
            offset += 1;

            this.externalErrors = unpack(view.getUint8(offset));
            offset += 1;

            this.internalErrors = unpack(view.getUint8(offset));
            offset += 1;
        },

        setCharging(value) {
            this.active = value;
            const appStore = useAppStore();
            appStore.writeState(setChargingUUID, pack_bool(value));
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(usePSUStore, import.meta.hot));
}
