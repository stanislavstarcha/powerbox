<template>
    <q-page class="">
        <div class="text-h5 q-mt-lg text-bold">Головний контролер</div>
        <div class="row q-mt-md">
            <div class="col-10">Версія</div>
            <div class="col">{{ espStore.version }}</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">Температура</div>
            <div class="col-2">{{ espStore.temperature }} ℃</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">Памʼять</div>
            <div class="col-2">{{ espStore.memory }}%</div>
        </div>
        <div class="row q-mt-md">
            <div class="col-10">Час роботи</div>
            <div class="col">{{ espStore.uptime }}</div>
        </div>
    </q-page>
</template>

<script setup>
import { ref } from "vue";
import { useESPStore } from "stores/esp";

const espStore = useESPStore();
</script>
