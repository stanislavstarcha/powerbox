import { acceptHMRUpdate, defineStore } from "pinia";
import { unpack, to_hex } from "src/utils/ble.js";

export const useESPStore = defineStore("esp", {
    state: () => ({
        version: null,
        uptime: 0,
        temperature: null,
        memory: null,
        internalErrors: null,
    }),

    actions: {
        parseState(view) {
            let offset = 0;

            this.uptime = unpack(view.getUint32(offset));
            offset += 4;

            const version = unpack(view.getUint16(offset));
            const major = (version >> 13) & 0x07; // 3 bits (111)
            const minor = (version >> 8) & 0x1f; // 5 bits (11111)
            const patch = version & 0xff; // 8 bits (11111111)
            this.version = major + "." + minor + "." + patch;
            offset += 2;

            this.temperature = unpack(view.getUint8(offset, true));
            offset += 1;

            this.memory = unpack(view.getUint8(offset));
            offset += 1;

            this.internalErrors = unpack(view.getUint8(offset));
            offset += 1;
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useESPStore, import.meta.hot));
}
