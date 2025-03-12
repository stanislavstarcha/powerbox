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
            <div class="col-10">{{ $t("acVoltage") }}</div>
            <div class="col-2" v-if="psuStore.ac">{{ psuStore.ac }} В</div>
            <div class="col-2 text-grey-5" v-if="!psuStore.ac">&mdash;</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("temperature") }} #1</div>
            <div class="col-2" v-if="psuStore.t1">{{ psuStore.t1 }} ℃</div>
            <div class="col-2 text-grey-5" v-if="!psuStore.t1">&mdash;</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("temperature") }} #2</div>
            <div class="col-2" v-if="psuStore.t2">{{ psuStore.t2 }} ℃</div>
            <div class="col-2 text-grey-5" v-if="!psuStore.t2">&mdash;</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("rpm") }}</div>
            <div class="col-2" v-if="psuStore.t2">{{ psuStore.rpm }} ℃</div>
            <div class="col-2 text-grey-5" v-if="!psuStore.rpm">&mdash;</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("power") }}</div>
            <div class="col-2" v-if="psuStore.power1">
                {{ psuStore.power1 }} ℃
            </div>
            <div class="col-2 text-grey-5" v-if="!psuStore.power1">&mdash;</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("maxChargingCurrent") }}</div>
            <div class="col-2" v-if="psuStore.currentChannel">
                {{ (psuStore.currentChannel + 1) * 25 }}%
            </div>
            <div class="col-2 text-grey-5" v-if="!psuStore.currentChannel">
                &mdash;
            </div>
        </div>
    </q-page>
</template>

<script setup>
import { computed, ref } from "vue";
import { usePSUStore } from "stores/psu";
import {
    HISTORY_PSU_RPM,
    HISTORY_PSU_POWER_1,
    HISTORY_PSU_POWER_2,
    HISTORY_PSU_TEMPERATURE_1,
    HISTORY_PSU_TEMPERATURE_2,
} from "stores/uuids.js";
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
                format: "{value}}℃",
                align: "left",
                x: 5,
                y: 10,
            },
            gridLineWidth: 0,
            lineWidth: 0,
        },
        {
            opposite: true,
            max: 100,
            title: { text: null },
            visible: true,
            tickPositions: [0, 50, 100],
            labels: {
                style: { fontSize: "9px" },
                format: "{value}",
                align: "left",
                x: -25,
                y: 10,
            },
            gridLineWidth: 0,
            lineWidth: 0,
        },
        {
            opposite: true,
            max: 42000,
            title: { text: null },
            visible: true,
            tickPositions: [0, 25, 75],
            labels: {
                style: { fontSize: "9px" },
                format: "{value}",
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
            data: psuStore.chartData[HISTORY_PSU_TEMPERATURE_1],
            yAxis: 0,
        },
        {
            data: psuStore.chartData[HISTORY_PSU_TEMPERATURE_2],
            yAxis: 0,
        },
        {
            data: psuStore.chartData[HISTORY_PSU_POWER_1],
            yAxis: 1,
        },
        {
            data: psuStore.chartData[HISTORY_PSU_POWER_2],
            yAxis: 1,
        },
        {
            data: psuStore.chartData[HISTORY_PSU_RPM],
            yAxis: 1,
        },
    ],
});
</script>
