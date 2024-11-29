<template>
    <q-page class="">
        <div class="text-h5 q-mt-lg text-bold">{{ $t("mainController") }}</div>
        <div class="row q-mt-md">
            <div class="col-10">{{ $t("version") }}</div>
            <div class="col">{{ espStore.version }}</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("temperature") }}</div>
            <div class="col-2">{{ espStore.temperature }} ℃</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("memory") }}</div>
            <div class="col-2">{{ espStore.memory }}%</div>
        </div>
        <div class="row q-mt-md">
            <div class="col-10">{{ $t("uptime") }}</div>
            <div class="col">{{ espStore.uptime }}</div>
        </div>
    </q-page>
</template>

<script setup>
import { ref } from "vue";
import { useESPStore } from "stores/esp";
import { useI18n } from "vue-i18n";
const { t } = useI18n();
const espStore = useESPStore();
</script>
