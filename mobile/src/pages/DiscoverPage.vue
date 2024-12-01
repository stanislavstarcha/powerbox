<template>
    <q-page class="">
        <div class="row flex-center">
            <div
                v-if="!appStore.scanning && !appStore.devices.length"
                class="col-6 justify-center text-center"
            >
                {{ $t("noStationsFound") }}
            </div>
        </div>

        <q-list v-if="appStore.devices">
            <q-item v-for="device in appStore.devices" :key="device.deviceId">
                <q-item-section avatar>
                    <q-icon name="flaticon-electric-station" />
                </q-item-section>

                <q-item-section>
                    <q-item-label>{{ device.name }}</q-item-label>
                    <q-item-label caption>{{ device.deviceId }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                    <q-btn flat @click="connect(device.deviceId)">{{
                        $t("connect")
                    }}</q-btn>
                </q-item-section>
            </q-item>
        </q-list>

        <div class="row flex-center" v-if="!appStore.scanning">
            <q-btn color="primary" @click="appStore.scan()" class="q-mt-md">{{
                $t("scanAgain")
            }}</q-btn>
        </div>

        <div class="row flex-center q-mt-xl">
            <a
                v-if="appStore.language === 'uk'"
                href="javascript:;"
                color="primary"
                @click="appStore.setLanguage('en')"
                class="q-mt-md"
                >Switch to English</a
            >
            <a
                v-if="appStore.language === 'en'"
                href="javascript:;"
                color="primary"
                @click="appStore.setLanguage('uk')"
                class="q-mt-md"
                >Перейти на українську</a
            >
        </div>
    </q-page>
</template>

<script setup>
import { useAppStore } from "stores/app";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";

const appStore = useAppStore();
const router = useRouter();
const { t } = useI18n();

appStore.bootstrap().then((response) => {
    appStore.scan().then(() => {
        appStore.initialised = true;
    });
});

const connect = (deviceId) => {
    appStore.connect(deviceId).then((response) => {
        router.push({ name: "Home" });
    });
};
</script>
