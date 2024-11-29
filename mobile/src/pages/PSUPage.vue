<template>
    <q-page class="">
        <highcharts :options="chartOptions"></highcharts>
        <div class="text-h5 q-mt-lg text-bold">{{ $t("psu") }}</div>
        <div v-if="psuStore.hasErrors()">
            <div v-for="error in errors" :key="error" class="error-message">
                {{ error }}
            </div>
        </div>
        <div class="row q-mt-md">
            <div class="col-10">{{ $t("voltage") }}</div>
            <div class="col-2" v-if="psuStore.voltage">
                {{ psuStore.voltage?.toFixed(2) }} В
            </div>
            <div class="col-2 text-grey-5" v-if="!psuStore.voltage">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("temperature") }}</div>
            <div class="col-2" v-if="psuStore.temperature">
                {{ psuStore.temperature }} ℃
            </div>
            <div class="col-2 text-grey-5" v-if="!psuStore.temperature">
                &mdash;
            </div>
        </div>
    </q-page>
</template>

<script setup>
import { computed, ref } from "vue";
import { usePSUStore } from "stores/psu";
import { HISTORY_PSU_TEMPERATURE } from "stores/uuids.js";
import { useI18n } from "vue-i18n";

const psuStore = usePSUStore();
const { t } = useI18n();

const errors = computed(() => {
    if (!psuStore.internalErrors) return [];

    const results = [];

    if (psuStore.internalErrors & (1 << 0)) {
        results.push(t("psuErrorTimeout"));
    }

    if (psuStore.internalErrors & (1 << 1)) {
        results.push(t("psuErrorException"));
    }

    if (psuStore.internalErrors & (1 << 4)) {
        results.push(t("psuErrorTemperatureSensor"));
    }

    if (psuStore.internalErrors & (1 << 5)) {
        results.push(t("psuErrorVoltageSensor"));
    }

    if (psuStore.internalErrors & (1 << 6)) {
        results.push(t("psuErrorPin"));
    }

    return results;
});

const chartOptions = ref({
    chart: {
        type: "spline",
        backgroundColor: "transparent",
        spacing: [0, 0, 0, 0],
        margin: [0, 0, 10, 0],
        height: 100,
    },
    title: {
        text: null,
    },
    xAxis: {
        visible: false,
    },
    yAxis: [
        {
            opposite: false,
            title: { text: null },
            visible: true,
            max: 15,
            tickPositions: [0, 12, 15],
            labels: {
                style: { fontSize: "9px" },
                format: "{value}" + t("volt"),
                align: "left",
                x: 5,
                y: 10,
            },
            gridLineWidth: 0,
            lineWidth: 0,
        },
        {
            opposite: true,
            max: 120,
            title: { text: null },
            visible: true,
            tickPositions: [0, 50, 100],
            labels: {
                style: { fontSize: "9px" },
                format: "{value}℃",
                align: "left",
                x: -25,
                y: 10,
            },
            gridLineWidth: 0,
            lineWidth: 0,
        },
    ],
    legend: {
        enabled: false,
    },
    credits: {
        enabled: false,
    },
    tooltip: {
        enabled: false,
    },
    plotOptions: {
        series: {
            marker: {
                enabled: false,
            },
            clip: false,
            lineWidth: 4,
            lineColor: "red",
            animation: false,
        },
    },
    series: [
        {
            data: psuStore.chartData[HISTORY_PSU_TEMPERATURE],
        },
    ],
});
</script>
