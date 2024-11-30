import { acceptHMRUpdate, defineStore } from "pinia";
import { unpack, unpack_bool, pack_bool } from "src/utils/ble.js";
import { useBLEStore } from "stores/ble.js";
import { setATSUUID } from "stores/uuids.js";

export const useATSStore = defineStore("ats", {
    state: () => ({
        active: false,
    }),

    actions: {
        parseState(view) {
            let offset = 0;

            this.active = unpack_bool(view.getUint8(offset));
            offset += 1;

            this.internalErrors = unpack(view.getUint8(offset));
            offset += 1;
        },

        set(value) {
            this.active = value;
            const bleStore = useBLEStore();
            bleStore.writeState(setATSUUID, pack_bool(value));
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useATSStore, import.meta.hot));
}
