import { acceptHMRUpdate, defineStore } from "pinia";
import { unpack, unpack_version } from "src/utils/ble.js";
import { dataViewToHexDump } from "src/utils/index.js";

export const useMCUStore = defineStore("esp", {
    state: () => ({
        uptime: 0,
        version: null,
        temperature: null,
        memory: null,
        internalErrors: null,
    }),

    actions: {
        parseState(view) {
            let offset = 0;
            console.log("MCU state", dataViewToHexDump(view));

            this.uptime = unpack(view.getUint32(offset));
            offset += 4;

            this.version = unpack_version(view.getUint8(offset));
            offset += 1;

            this.temperature = unpack(view.getUint8(offset));
            offset += 1;

            this.memory = unpack(view.getUint8(offset));
            offset += 1;

            this.internalErrors = unpack(view.getUint8(offset));
            offset += 1;
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useMCUStore, import.meta.hot));
}
