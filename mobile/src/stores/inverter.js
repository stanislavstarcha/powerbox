import _ from "underscore";
import { acceptHMRUpdate, defineStore } from "pinia";
import { unpack, unpack_bool, unpack_voltage } from "src/utils/ble.js";
import { useBLEStore } from "stores/ble.js";
import {
    dischargingUUID,
    HISTORY_INVERTER_POWER,
    HISTORY_INVERTER_TEMPERATURE,
} from "stores/uuids.js";

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
            const bleStore = useBLEStore();
            bleStore.writeState(dischargingUUID, value);
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useInverterStore, import.meta.hot));
}
