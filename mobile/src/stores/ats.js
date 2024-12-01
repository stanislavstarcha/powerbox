import { acceptHMRUpdate, defineStore } from "pinia";
import { unpack, unpack_bool } from "src/utils/ble.js";

export const useATSStore = defineStore("ats", {
    state: () => ({
        active: false,
        enabled: false,
    }),

    actions: {
        parseState(view) {
            let offset = 0;

            this.active = unpack_bool(view.getUint8(offset));
            offset += 1;

            this.internalErrors = unpack(view.getUint8(offset));
            offset += 1;
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useATSStore, import.meta.hot));
}
