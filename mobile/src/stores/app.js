import { acceptHMRUpdate, defineStore } from "pinia";

export const useAppStore = defineStore("app", {
    state: () => ({
        initialized: false,
        deviceId: null,
        devices: [],
    }),

    actions: {
        addDevice(device) {
            this.devices.push(device);
        },

        clearDevices() {
            this.devices = [];
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useAppStore, import.meta.hot));
}
