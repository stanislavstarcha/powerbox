<template>
    <q-layout view="lHh Lpr lFf">
        <q-header>
            <q-toolbar class="flex-center">
                <img src="~assets/logo-lg.png" height="32" />
                <router-link to="/help"> </router-link>
            </q-toolbar>
        </q-header>

        <q-footer
            bordered
            class="bg-grey-3 text-primary"
            v-if="bleStore.deviceId"
        >
            <q-tabs
                no-caps
                active-color="primary"
                indicator-color="transparent"
                class="text-grey-8"
                v-model="tab"
            >
                <q-route-tab name="home" to="/home" icon="flaticon-home" />
                <q-route-tab name="bms" to="/bms" icon="flaticon-hub">
                    <q-badge v-if="bmsStore.hasErrors()" color="red" floating
                        >!</q-badge
                    >
                </q-route-tab>
                <q-route-tab
                    name="inverter"
                    to="/inverter"
                    icon="flaticon-ac-voltage-source"
                />
                <q-route-tab name="psu" to="/psu" icon="flaticon-psu">
                    <q-badge v-if="psuStore.hasErrors()" color="red" floating
                        >!</q-badge
                    >
                </q-route-tab>
                <q-route-tab name="esp" to="/esp" icon="flaticon-cpu">
                    <q-badge v-if="espStore.hasErrors()" color="red" floating
                        >!</q-badge
                    >
                </q-route-tab>
            </q-tabs>
        </q-footer>

        <q-page-container>
            <router-view />
        </q-page-container>
    </q-layout>
</template>

<script setup>
import { ref } from "vue";
import { useBLEStore } from "stores/ble";
import { useBMSStore } from "stores/bms";
import { usePSUStore } from "stores/psu";
import { useInverterStore } from "stores/inverter";
import { useESPStore } from "stores/esp";

const bleStore = useBLEStore();
const bmsStore = useBMSStore();
const espStore = useESPStore();
const psuStore = usePSUStore();
const inverterStore = useInverterStore();

const tab = ref();
</script>
