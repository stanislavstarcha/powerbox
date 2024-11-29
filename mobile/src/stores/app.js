import { acceptHMRUpdate, defineStore } from "pinia";
import { i18n } from "src/boot/i18n";

export const useAppStore = defineStore("app", {
    state: () => ({
        language: i18n.global.locale,
        initialized: false,
        deviceId: null,
        devices: [],
    }),

    actions: {
        setLanguage(language) {
            i18n.global.locale = language;
            this.language = language;
        },
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
