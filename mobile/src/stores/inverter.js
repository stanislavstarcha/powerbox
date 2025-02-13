import { acceptHMRUpdate, defineStore } from "pinia";
import { unpack, unpack_bool } from "src/utils/ble.js";
import {
    HISTORY_INVERTER_POWER,
    HISTORY_INVERTER_TEMPERATURE,
    COMMAND_INVERTER_ENABLE,
    COMMAND_INVERTER_DISABLE,
    COMMAND_PSU_ENABLE,
    COMMAND_PSU_DISABLE,
} from "stores/uuids.js";
import { useAppStore } from "stores/app.js";

export const useInverterStore = defineStore("inverter", {
    state: () => ({
        ac: null,
        power: null,
        temperature: null,

        externalErrors: null,
        internalErrors: null,

        chartData: {},
        chartMappings: {
            [HISTORY_INVERTER_POWER]: unpack,
            [HISTORY_INVERTER_TEMPERATURE]: unpack,
        },
    }),

    actions: {
        parseState(view) {
            let offset = 0;

            this.power = unpack(view.getUint16(offset));
            offset += 2;

            this.active = unpack_bool(view.getUint8(offset));
            offset += 1;

            this.ac = unpack(view.getUint8(offset));
            offset += 1;

            this.temperature = unpack(view.getUint8(offset));
            offset += 1;

            this.externalErrors = unpack(view.getUint8(offset));
            offset += 1;

            this.internalErrors = unpack(view.getUint8(offset));
            offset += 1;
        },

        setDischarging(value) {
            this.active = value;
            const appStore = useAppStore();
            if (value) {
                appStore.runBLECommand(COMMAND_INVERTER_ENABLE);
            } else {
                appStore.runBLECommand(COMMAND_INVERTER_DISABLE);
            }
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useInverterStore, import.meta.hot));
}
