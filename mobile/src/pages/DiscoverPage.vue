<template>
    <q-page class="">
        <div class="row flex-center">
            <div
                v-if="!bleStore.scanning && !bleStore.devices.length"
                class="col-6 justify-center text-center"
            >
                Не знайдено жодної станції. Переконайтесь що вона ввімкнена та
                знаходиться поблизу.
            </div>
        </div>

        <q-list v-if="bleStore.devices">
            <q-item v-for="device in bleStore.devices" :key="device.deviceId">
                <q-item-section avatar>
                    <q-icon name="flaticon-electric-station" />
                </q-item-section>

                <q-item-section>
                    <q-item-label>{{ device.name }}</q-item-label>
                    <q-item-label caption>{{ device.deviceId }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                    <q-btn flat @click="connect(device.deviceId)"
                        >connect</q-btn
                    >
                </q-item-section>
            </q-item>
        </q-list>

        <div class="row flex-center" v-if="!bleStore.scanning">
            <q-btn color="primary" @click="bleStore.scan()" class="q-mt-md"
                >Шукати знов</q-btn
            >
        </div>
    </q-page>
</template>

<script setup>
import { useAppStore } from "stores/app";
import { useBLEStore } from "stores/ble";
import { useRouter } from "vue-router";

const appStore = useAppStore();
const bleStore = useBLEStore();
const router = useRouter();

bleStore.bootstrap().then((response) => {
    bleStore.scan().then(() => {
        appStore.initialized = true;
    });
});

const connect = (deviceId) => {
    bleStore.connect(deviceId).then((response) => {
        router.push({ name: "Home" });
    });
};
</script>
