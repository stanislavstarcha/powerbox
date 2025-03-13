import { acceptHMRUpdate, defineStore } from "pinia";
import { unpack, unpack_bool, unpack_voltage } from "src/utils/ble.js";

import {
    HISTORY_PSU_RPM,
    HISTORY_PSU_TEMPERATURE_1,
    HISTORY_PSU_TEMPERATURE_2,
    HISTORY_PSU_POWER_1,
    HISTORY_PSU_POWER_2,
    COMMAND_PSU_ENABLE,
    COMMAND_PSU_DISABLE,
} from "stores/uuids.js";
import { useAppStore } from "stores/app.js";
import { dataViewToHexDump } from "src/utils/index.js";

export const usePSUStore = defineStore("psu", {
    state: () => ({
        rpm: null,
        power1: null,
        power2: null,
        ac: null,
        t1: null,
        t2: null,
        active: null,
        currentChannel: null,
        externalErrors: null,
        internalErrors: null,
        chartData: {},
        chartMappings: {
            [HISTORY_PSU_RPM]: unpack,
            [HISTORY_PSU_TEMPERATURE_1]: unpack,
            [HISTORY_PSU_TEMPERATURE_2]: unpack,
            [HISTORY_PSU_POWER_1]: unpack,
            [HISTORY_PSU_POWER_2]: unpack,
        },
    }),

    actions: {
        parseState(view) {
            let offset = 0;
            console.log("PSU state", dataViewToHexDump(view));

            this.rpm = unpack(view.getUint16(offset));
            offset += 2;

            this.power1 = unpack(view.getUint16(offset));
            offset += 2;

            this.power2 = unpack(view.getUint16(offset));
            offset += 2;

            this.ac = unpack(view.getUint8(offset));
            offset += 1;

            this.t1 = unpack(view.getUint8(offset));
            offset += 1;

            this.t2 = unpack(view.getUint8(offset));
            offset += 1;

            this.channel = unpack(view.getUint8(offset));
            offset += 1;

            this.active = unpack_bool(view.getUint8(offset));
            offset += 1;

            this.externalErrors = unpack(view.getUint8(offset));
            offset += 1;

            this.internalErrors = unpack(view.getUint8(offset));
            offset += 1;
        },

        setCharging(value) {
            this.active = value;
            const appStore = useAppStore();
            if (value) {
                console.log("Enabling PSU");
                appStore.runBLECommand(COMMAND_PSU_ENABLE);
            } else {
                console.log("Disabling PSU");
                appStore.runBLECommand(COMMAND_PSU_DISABLE);
            }
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(usePSUStore, import.meta.hot));
}
