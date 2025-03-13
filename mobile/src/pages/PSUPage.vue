<template>
    <q-page class="">
        <highcharts :options="chartOptions"></highcharts>

        <div class="text-h5 q-mt-lg text-bold">{{ $t("psu") }}</div>
        <div class="q-mt-md error-message" v-for="error in errors" :key="error">
            {{ error }}
        </div>

        <div class="row q-mt-md">
            <div class="col-9"><span>■</span> {{ $t("acVoltage") }}</div>
            <div class="col text-right" v-if="psuStore.ac">
                {{ psuStore.ac }}{{ $t("volt") }}
            </div>
            <div class="col text-right text-grey-5" v-if="!psuStore.ac">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: TEMPERATURE_COLOR }">■</span>
                {{ $t("temperature") }} #1
            </div>
            <div class="col text-right" v-if="psuStore.t1">
                {{ psuStore.t1 }}℃
            </div>
            <div class="col text-right text-grey-5" v-if="!psuStore.t1">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: TEMPERATURE_COLOR }">■</span>
                {{ $t("temperature") }} #2
            </div>
            <div class="col text-right" v-if="psuStore.t2">
                {{ psuStore.t2 }}℃
            </div>
            <div class="col text-right text-grey-5" v-if="!psuStore.t2">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: FAN_COLOR }">■</span>
                {{ $t("fan_speed") }}
            </div>
            <div class="col text-right" v-if="psuStore.t2">
                {{ psuStore.rpm }} {{ $t("rpm") }}
            </div>
            <div class="col text-right text-grey-5" v-if="!psuStore.rpm">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: POWER_COLOR }">■</span> {{ $t("power") }}
            </div>
            <div class="col text-right" v-if="psuStore.power2">
                {{ psuStore.power2 }}{{ $t("watt") }}
            </div>
            <div class="col text-right text-grey-5" v-if="!psuStore.power2">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">■ {{ $t("maxChargingCurrent") }}</div>
            <div class="col text-right" v-if="appStore.currentLimit">
                {{ (appStore.currentLimit + 1) * 25 }}%
            </div>
            <div
                class="col text-right text-grey-5"
                v-if="!appStore.currentLimit"
            >
                &mdash;
            </div>
        </div>
    </q-page>
</template>

<script setup>
import { computed, ref } from "vue";
import { usePSUStore } from "stores/psu";
import { useAppStore } from "stores/app.js";
import {
    HISTORY_PSU_RPM,
    HISTORY_PSU_POWER_1,
    HISTORY_PSU_POWER_2,
    HISTORY_PSU_TEMPERATURE_1,
    HISTORY_PSU_TEMPERATURE_2,
    FAN_COLOR,
    TEMPERATURE_COLOR,
    POWER_COLOR,
} from "stores/uuids.js";
import { useI18n } from "vue-i18n";
import { getErrors } from "src/utils/index.js";

const appStore = useAppStore();
const psuStore = usePSUStore();

const { t } = useI18n();

const errors = computed(() => {
    return getErrors(
        "psu",
        psuStore.internalErrors ?? 0,
        psuStore.externalErrors ?? 0,
        t,
    );
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
            max: 100,
            tickPositions: [0, 50, 100],
            labels: {
                style: { color: TEMPERATURE_COLOR, fontSize: "9px" },
                format: "{value}℃",
                align: "left",
                x: 5,
                y: 10,
            },
            gridLineWidth: 0,
            lineWidth: 0,
        },
        {
            opposite: true,
            max: 50000,
            title: { text: null },
            visible: true,
            tickPositions: [0, 20000, 50000],
            labels: {
                style: { color: FAN_COLOR, fontSize: "9px" },
                format: "{value} " + t("rpm"),
                align: "left",
                x: -55,
                y: 10,
            },
            gridLineWidth: 0,
            lineWidth: 0,
        },
        {
            opposite: true,
            max: 1500,
            title: { text: null },
            visible: true,
            tickPositions: [0, 600, 1400],
            labels: {
                style: { color: POWER_COLOR, fontSize: "9px" },
                format: "{value}" + t("watt"),
                align: "left",
                x: -90,
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
            lineWidth: 2,
            lineColor: TEMPERATURE_COLOR,
            yAxis: 0,
            connectNulls: false,
        },
        {
            data: psuStore.chartData[HISTORY_PSU_TEMPERATURE_2],
            lineWidth: 2,
            lineColor: TEMPERATURE_COLOR,
            yAxis: 0,
            connectNulls: false,
        },
        {
            data: psuStore.chartData[HISTORY_PSU_RPM],
            lineWidth: 2,
            lineColor: FAN_COLOR,
            yAxis: 1,
            connectNulls: false,
        },
        {
            data: psuStore.chartData[HISTORY_PSU_POWER_2],
            lineWidth: 2,
            lineColor: POWER_COLOR,
            yAxis: 2,
            connectNulls: false,
        },
    ],
});
</script>
