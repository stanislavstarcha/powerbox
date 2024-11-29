<template>
    <q-page class="">
        <highcharts :options="chartOptions"></highcharts>

        <div class="text-h5 q-mt-lg text-bold">{{ $t("inverter") }}</div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("acVoltage") }}</div>
            <div class="col-2" v-if="inverterStore.ac">
                {{ inverterStore.ac }} В
            </div>
            <div class="col-2 text-grey-5" v-if="!inverterStore.ac">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("consumption") }}</div>
            <div class="col-2" v-if="inverterStore.power">
                {{ inverterStore.power }} {{ $t("watt") }}
            </div>
            <div class="col-2 text-grey-5" v-if="!inverterStore.power">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("temperature") }}</div>
            <div class="col-2" v-if="inverterStore.temperature">
                {{ inverterStore.temperature }} ℃
            </div>
            <div class="col-2 text-grey-5" v-if="!inverterStore.temperature">
                &mdash;
            </div>
        </div>
    </q-page>
</template>

<script setup>
import { computed, ref } from "vue";
import { useInverterStore } from "stores/inverter";
import {
    HISTORY_INVERTER_POWER,
    HISTORY_INVERTER_TEMPERATURE,
} from "stores/uuids.js";
import { useI18n } from "vue-i18n";

const inverterStore = useInverterStore();
const { t } = useI18n();

const errors = computed(() => {
    if (!inverterStore.internalErrors) return [];

    const results = [];

    if (inverterStore.internalErrors & (1 << 0)) {
        results.push(t("inverterErrorTimeout"));
    }

    if (inverterStore.internalErrors & (1 << 1)) {
        results.push(t("inverterErrorException"));
    }

    if (inverterStore.internalErrors & (1 << 2)) {
        results.push(t("inverterErrorNoResponse"));
    }

    if (inverterStore.internalErrors & (1 << 3)) {
        results.push(t("inverterErrorBadResponse"));
    }

    if (inverterStore.externalErrors == 10) {
        results.push(t("inverterErrorUnderVoltage"));
    }

    if (inverterStore.externalErrors == 20) {
        results.push(t("inverterErrorOverVoltage"));
    }

    return results;
});

const chartOptions = ref({
    chart: {
        type: "spline",
        backgroundColor: "transparent",
        spacing: [0, 0, 0, 0], // Removes outer spacing around the chart
        margin: [0, 0, 10, 0], // Removes margins within the chart area
        height: 100,
    },
    title: {
        text: null, // Hides title
    },
    xAxis: {
        visible: false, // Hides the x-axis completely
    },
    yAxis: [
        {
            opposite: false,
            title: { text: null },
            visible: true,
            max: 2500,
            tickPositions: [0, 1000, 2500],
            labels: {
                style: { fontSize: "9px" },
                format: "{value} " + t("watt"),
                align: "left",
                x: 5,
                y: 10,
            },
            gridLineWidth: 0,
            lineWidth: 0, // Hide grid and axis lines
        },
        {
            opposite: true,
            max: 75,
            title: { text: null },
            visible: true,
            tickPositions: [0, 25, 75],
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
        enabled: false, // Hides the legend
    },
    credits: {
        enabled: false, // Removes the Highcharts watermark
    },
    tooltip: {
        enabled: false, // Disables tooltips
    },
    plotOptions: {
        series: {
            marker: {
                enabled: false, // Disables point markers
            },
            clip: false,
        },
    },
    series: [
        {
            data: inverterStore.chartData[HISTORY_INVERTER_POWER],
            lineWidth: 4,
            lineColor: "red",
            yAxis: 0,
            animation: false,
        },
        {
            data: inverterStore.chartData[HISTORY_INVERTER_TEMPERATURE],
            lineWidth: 1,
            lineColor: "green",
            yAxis: 1,
            animation: false,
        },
    ],
});
</script>
