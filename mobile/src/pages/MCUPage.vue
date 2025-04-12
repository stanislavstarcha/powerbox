<template>
    <q-page class="hide-bottom-space">
        <div class="text-h5 q-mt-lg text-bold">{{ $t("mainController") }}</div>
        <div class="q-mt-md error-message" v-for="error in errors" :key="error">
            {{ error }}
        </div>

        <div v-if="mcuStore.updateAvailable" class="row q-mt-md q-mb-md">
            <q-btn class="col-12" color="primary" @click="showOTADialog()"
                >{{ $t("newVersionAvailable") }}
                {{ mcuStore.remoteVersion }}</q-btn
            >
            <div class="q-pa-lg" v-if="OTADialog">
                {{ $t("selectWifiPassword") }}

                <q-input
                    class="q-mt-md"
                    outlined
                    v-model="ssid"
                    :label="$t('wifiNetwork')"
                    :autocorrect="'off'"
                    :autocomplete="'off'"
                    :spellcheck="false"
                ></q-input>

                <q-input
                    class="q-mt-md"
                    outlined
                    v-model="password"
                    type="password"
                    :label="$t('wifiPassword')"
                    :autocorrect="'off'"
                    :autocomplete="'off'"
                    :spellcheck="false"
                />
                <q-btn
                    class="col-4 q-mt-md"
                    color="secondary"
                    @click="startOTAUpdate()"
                    >{{ $t("startFirmwareUpdate") }}</q-btn
                >
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-8">{{ $t("version") }}</div>
            <div class="col text-right">{{ mcuStore.version }}</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-8">{{ $t("temperature") }}</div>
            <div class="col text-right">{{ mcuStore.temperature }} ℃</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-8">{{ $t("memory") }}</div>
            <div class="col text-right">{{ 100 - mcuStore.memory }}%</div>
        </div>
        <div class="row q-mt-md">
            <div class="col-8">{{ $t("uptime") }}</div>
            <div class="col text-right">
                {{ formatTimeElapsed(mcuStore.uptime) }}
            </div>
        </div>
        <div class="row q-mt-md items-center">
            <div class="col-9">{{ $t("avrMode") }}</div>
            <div class="col-3">
                <q-toggle
                    :color="ats ? 'red' : 'grey'"
                    v-model="ats"
                    size="70px"
                />
            </div>
        </div>
        <div class="row q-mt-md items-center">
            <div class="col-9">
                {{ $t("appLanguage") }}
                <br />
                <q-radio v-model="language" val="uk">Українська</q-radio>
                <br />
                <q-radio v-model="language" val="en">English</q-radio>
            </div>
        </div>
        <div class="row q-mt-md items-center">
            <a href="javascript:;" @click="showDebugPage()">{{
                $t("showDebugInfo")
            }}</a>
        </div>
    </q-page>
</template>

<script setup>
import { computed, ref, onMounted } from "vue";

import { useRouter } from "vue-router";
import { useAppStore } from "stores/app";
import { useMCUStore } from "stores/mcu";
import { useI18n } from "vue-i18n";
const { t } = useI18n();
const mcuStore = useMCUStore();
const appStore = useAppStore();

import { formatTimeElapsed, getErrors } from "src/utils/index.js";

const router = useRouter();
const OTADialog = ref(false);
const ssid = ref();
const password = ref();

const showOTADialog = () => {
    OTADialog.value = true;
};

const ats = computed({
    get: () => appStore.ats,
    set: (value) => {
        appStore.setATS(value);
    },
});

const language = computed({
    get: () => appStore.language,
    set: (value) => {
        appStore.setLanguage(value);
    },
});

const startOTAUpdate = () => {
    mcuStore.setOTACredentials(ssid.value, password.value).then(() => {
        mcuStore.updateFirmware();
    });
};

const showDebugPage = () => {
    router.push({ name: "DEBUG" });
};

onMounted(async () => {
    ssid.value = await appStore.getPreference("ota_ssid");
    password.value = await appStore.getPreference("ota_password");
    // Keyboard.setAccessoryBarVisible({ isVisible: false });
});

const errors = computed(() => {
    return getErrors("mcu", mcuStore.internalErrors ?? 0, 0, t);
});

const disconnect = () => {
    appStore.disconnect();
};
</script>
