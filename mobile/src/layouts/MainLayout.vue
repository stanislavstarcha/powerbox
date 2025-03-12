<template>
    <q-layout view="lHh Lpr lFf">
        <q-header>
            <q-toolbar class="flex-center">
                <img src="~assets/logo-lg.png" height="32" />
                <router-link to="/help"> </router-link>
            </q-toolbar>
        </q-header>

        <q-footer bordered class="bg-grey-3 text-primary">
            <q-tabs
                v-if="appStore.deviceId"
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
                >
                    <q-badge
                        v-if="inverterStore.hasErrors()"
                        color="red"
                        floating
                        >!</q-badge
                    >
                </q-route-tab>
                <q-route-tab name="psu" to="/psu" icon="flaticon-psu">
                    <q-badge v-if="psuStore.hasErrors()" color="red" floating
                        >!</q-badge
                    >
                </q-route-tab>
                <q-route-tab name="esp" to="/esp" icon="flaticon-cpu">
                    <q-badge v-if="mcuStore.hasErrors()" color="red" floating
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
import { useAppStore } from "stores/app";
import { useBMSStore } from "stores/bms";
import { usePSUStore } from "stores/psu";
import { useInverterStore } from "stores/inverter";
import { useMCUStore } from "stores/mcu";

const appStore = useAppStore();
const bmsStore = useBMSStore();
const mcuStore = useMCUStore();
const psuStore = usePSUStore();
const inverterStore = useInverterStore();

const tab = ref();
</script>
