import axios from "axios";
import { acceptHMRUpdate, defineStore } from "pinia";
import { Loading, QSpinnerGears } from "quasar";
import { numbersToDataView } from "@capacitor-community/bluetooth-le";

import { unpack, unpack_version } from "src/utils/ble.js";
import { i18n } from "src/boot/i18n";

import {
    dataViewToHexDump,
    pack_bool_param,
    pack_float_param,
    pack_int_param,
    pack_string_param,
} from "src/utils/index.js";

import {
    PROFILE_KEY_ATS,
    PROFILE_KEY_WIFI_SSID,
    PROFILE_KEY_WIFI_PASSWORD,
    PROFILE_KEY_PSU_CURRENT,
    PROFILE_KEY_MIN_VOLTAGE,
    PROFILE_KEY_MAX_VOLTAGE,
    COMMAND_UPDATE_FIRMWARE,
} from "stores/uuids.js";

import { useAppStore } from "stores/app.js";

const OTA_STATUS_IDLE = 0;
const OTA_STATUS_PREPARING = 1;
const OTA_STATUS_DOWNLOADING = 2;
const OTA_STATUS_UPDATING = 3;
const OTA_STATUS_ERROR = 4;
const OTA_STATUS_FINISHED = 5;

export const useMCUStore = defineStore("esp", {
    state: () => ({
        uptime: 0,
        version: null,
        remoteVersion: null,
        updateAvailable: false,
        temperature: null,
        memory: null,
        internalErrors: null,
    }),

    actions: {
        parseOTAState(view) {
            let offset = 0;
            console.log("OTA state", dataViewToHexDump(view));

            this.status = unpack(view.getUint8(offset));
            offset += 1;

            this.progress = unpack(view.getUint8(offset));
            offset += 1;

            this.otaError = unpack(view.getUint8(offset));
            offset += 1;

            if (
                [
                    OTA_STATUS_IDLE,
                    OTA_STATUS_FINISHED,
                    OTA_STATUS_ERROR,
                ].includes(this.status)
            ) {
                Loading.hide();
            }

            if (this.status === OTA_STATUS_UPDATING) {
                console.log("OTA updating " + this.progress);
                Loading.show({
                    message:
                        i18n.global.t("otaUpdating") +
                        " " +
                        this.progress +
                        "%",
                    spinner: QSpinnerGears,
                });
            }

            if (this.status === OTA_STATUS_PREPARING) {
                console.log("OTA preparing...");
                Loading.show({
                    message: i18n.global.t("otaPreparing"),
                    spinner: QSpinnerGears,
                });
            }

            if (this.status === OTA_STATUS_DOWNLOADING) {
                console.log("Downloading");
                Loading.show({
                    message: i18n.global.t("otaDownloading"),
                    spinner: QSpinnerGears,
                });
            }
        },

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

        checkFirmwareUpdate() {
            axios
                .get(
                    "https://api.github.com/repos/stanislavstarcha/powerbox/releases/latest",
                )
                .then((response) => {
                    this.remoteVersion = response.data.tag_name;
                    this.updateAvailable = this.compareVersions(
                        this.version,
                        response.data.tag_name,
                    );
                });
        },

        compareVersions(current, newer) {
            if (!newer) newer = "0.0.0";
            if (!current) current = "0.0.0";

            const newerParts = newer.split(".").map(Number);
            const currentParts = current.split(".").map(Number);

            for (let i = 0; i < 3; i++) {
                if ((newerParts[i] || 0) > (currentParts[i] || 0)) return true;
                if ((newerParts[i] || 0) < (currentParts[i] || 0)) return false;
            }
            return false;
        },

        updateFirmware() {
            Loading.show({
                message: i18n.global.t("otaPreparing"),
                spinner: QSpinnerGears,
            });

            const appStore = useAppStore();
            appStore.runBLECommand(
                numbersToDataView([COMMAND_UPDATE_FIRMWARE]),
            );
        },

        async setOTACredentials(ssid, password) {
            const appStore = useAppStore();
            await appStore.runBLECommand(
                pack_string_param(PROFILE_KEY_WIFI_SSID, ssid),
            );
            await appStore.runBLECommand(
                pack_string_param(PROFILE_KEY_WIFI_PASSWORD, password),
            );
            await appStore.savePreference("ota_ssid", ssid);
            await appStore.savePreference("ota_password", password);
        },

        setProfileParam(param, value) {
            const appStore = useAppStore();

            appStore.runBLECommand(pack_bool_param(PROFILE_KEY_ATS, false));

            appStore.runBLECommand(
                pack_float_param(PROFILE_KEY_MIN_VOLTAGE, 2.8),
            );

            appStore.runBLECommand(
                pack_float_param(PROFILE_KEY_MAX_VOLTAGE, 3.4),
            );
        },

        subscribeToLogs(callback) {},
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useMCUStore, import.meta.hot));
}
