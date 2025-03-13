<template>
    <q-page class="">
        <highcharts :options="chartOptions"></highcharts>

        <div class="text-h5 q-mt-lg text-bold">{{ $t("inverter") }}</div>
        <div class="q-mt-md error-message" v-for="error in errors" :key="error">
            {{ error }}
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span>■</span>
                {{ $t("acVoltage") }}
            </div>
            <div class="col text-right" v-if="inverterStore.ac">
                {{ inverterStore.ac }} В
            </div>
            <div class="col text-right text-grey-5" v-if="!inverterStore.ac">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: POWER_COLOR }">■</span>
                {{ $t("consumption") }}
            </div>
            <div class="col text-right" v-if="inverterStore.power">
                {{ inverterStore.power }} {{ $t("watt") }}
            </div>
            <div class="col text-right text-grey-5" v-if="!inverterStore.power">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: TEMPERATURE_COLOR }">■</span>
                {{ $t("temperature") }}
            </div>
            <div class="col text-right" v-if="inverterStore.temperature">
                {{ inverterStore.temperature }} ℃
            </div>
            <div
                class="col text-right text-grey-5"
                v-if="!inverterStore.temperature"
            >
                &mdash;
            </div>
        </div>
        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: FAN_COLOR }">■</span>
                {{ $t("fan_speed") }}
            </div>
            <div class="col text-right" v-if="inverterStore.rpm">
                {{ inverterStore.rpm }} {{ $t("rpm") }}
            </div>
            <div class="col text-right text-grey-5" v-if="!inverterStore.rpm">
                –
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
    HISTORY_INVERTER_RPM,
    FAN_COLOR,
    TEMPERATURE_COLOR,
    POWER_COLOR,
} from "stores/uuids.js";
import { getErrors } from "src/utils/index.js";
import { useI18n } from "vue-i18n";

const inverterStore = useInverterStore();
const { t } = useI18n();

const errors = computed(() => {
    return getErrors(
        "inverter",
        inverterStore.internalErrors ?? 0,
        inverterStore.externalErrors ?? 0,
        t,
    );
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
                style: { color: POWER_COLOR, fontSize: "9px" },
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
            max: 55,
            title: { text: null },
            visible: true,
            tickPositions: [0, 30, 55],
            labels: {
                style: { color: TEMPERATURE_COLOR, fontSize: "9px" },
                format: "{value}℃",
                align: "left",
                x: -25,
                y: 10,
            },
            gridLineWidth: 0,
        },
        {
            opposite: false,
            max: 25000,
            title: { text: null },
            visible: true,
            tickPositions: [0, 10000, 25000],
            labels: {
                style: { color: FAN_COLOR, fontSize: "9px" },
                format: "{value} об/хв",
                align: "left",
                x: 50,
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
            lineColor: POWER_COLOR,
            yAxis: 0,
            animation: false,
        },
        {
            data: inverterStore.chartData[HISTORY_INVERTER_TEMPERATURE],
            lineWidth: 1,
            lineColor: TEMPERATURE_COLOR,
            yAxis: 1,
            animation: false,
        },
        {
            data: inverterStore.chartData[HISTORY_INVERTER_RPM],
            lineWidth: 1,
            lineColor: FAN_COLOR,
            yAxis: 2,
            animation: false,
        },
    ],
});
</script>
