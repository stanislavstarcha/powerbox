<template>
    <q-page>
        <div class="row justify-center items-center q-mt-lg">
            <div class="col col-auto">
                <q-icon :name="batteryIcon" :color="levelColor" size="64px" />
            </div>

            <div
                class="col col-auto text-h1 text-weight-bold text-center"
                :color="levelColor"
            >
                {{ bmsStore.level }}%
            </div>
        </div>

        <div class="row justify-center">
            <div class="col-auto text-caption text-grey-7 q-ml-xs">
                {{ $t("power") }}
            </div>
            <div class="col-auto q-ml-xs q-mr-lg">
                {{ inverterStore.power }} {{ $t("watt") }}
            </div>
            <div class="col-auto text-caption text-grey-7 q-ml-xs">
                {{ $t("voltage") }}
            </div>
            <div class="col-auto q-ml-xs q-mr-lg">
                {{ bmsStore.voltage }} {{ $t("volt") }}
            </div>
        </div>

        <highcharts :options="chartOptions" class="q-mt-md"></highcharts>

        <div class="row q-mt-md">
            <div class="col-6 text-center">
                <div class="text-h5 text-weight-bold">{{ $t("psu") }}</div>
                <div class="text-caption text-grey-5">
                    {{ $t("startPSU") }}
                </div>
                <q-toggle
                    :color="charging ? 'red' : 'grey'"
                    v-model="charging"
                    size="70px"
                />

                <div class="text-caption text-grey-5">
                    {{ $t("maxChargingCurrent") }}
                </div>
                <q-slider
                    class="q-pl-md q-pr-md"
                    v-model="currentLimit"
                    :disable="!charging"
                    :color="charging ? 'red' : 'grey'"
                    markers
                    thumb-size="20px"
                    track-size="5px"
                    :marker-labels="currentLimitLabels"
                    :min="0"
                    :max="3"
                />
            </div>
            <div class="col-6 text-center">
                <div class="text-h5 text-weight-bold">{{ $t("inverter") }}</div>
                <div class="text-caption text-grey-5">
                    {{ $t("startInverterAC") }}
                </div>
                <q-toggle
                    :color="discharging ? 'blue' : 'grey'"
                    v-model="discharging"
                    size="70px"
                />
            </div>
        </div>
    </q-page>
</template>

<script setup>
import { ref, computed } from "vue";
import { useBMSStore } from "stores/bms";
import { usePSUStore } from "stores/psu";
import { useInverterStore } from "stores/inverter";

import { HISTORY_BMS_SOC } from "stores/uuids";
import { useI18n } from "vue-i18n";

const bmsStore = useBMSStore();
const psuStore = usePSUStore();
const inverterStore = useInverterStore();
const { t } = useI18n();

const currentLimitLabels = ref({
    0: "25A",
    1: "50A",
    2: "75A",
    3: "100A",
});

const charging = computed({
    get: () => psuStore.active,
    set: (value) => {
        psuStore.setCharging(value);
    },
});

const discharging = computed({
    get: () => inverterStore.active,
    set: (value) => {
        inverterStore.setDischarging(value);
    },
});

const currentLimit = computed({
    get: () => psuStore.currentLimit,
    set: (value) => {
        psuStore.setCurrentLimit(value);
    },
});

const levelColor = computed(() => {
    if (bmsStore.level >= 80) return "green";
    if (bmsStore.level < 20) return "red";
    return "orange";
});

const batteryIcon = computed(() => {
    if (bmsStore.level >= 80) return "flaticon-battery-status-5";
    if (bmsStore.level >= 60) return "flaticon-battery-status-4";
    if (bmsStore.level >= 40) return "flaticon-battery-status-3";
    if (bmsStore.level >= 20) return "flaticon-battery-status-2";
    return "flaticon-battery-status-1";
});

const chartOptions = ref({
    chart: {
        type: "spline",
        backgroundColor: "transparent",
        spacing: [0, 0, 0, 0],
        margin: [10, 0, 10, 0],
        height: 100,
        animation: false,
    },
    title: {
        text: null,
    },
    xAxis: {
        visible: false,
    },
    yAxis: {
        max: 105,
        title: { text: null },
        visible: true,
        tickPositions: [0, 50, 100],
        labels: {
            style: { fontSize: "9px" },
            format: "{value}%",
            align: "left",
            x: 5,
            y: 10,
        },
        gridLineWidth: 0,
        lineWidth: 0,
    },
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
            animation: false,
            clip: false,
            lineWidth: 4,
        },
    },
    series: [
        {
            data: bmsStore.chartData[HISTORY_BMS_SOC],
            connectNulls: false,
        },
    ],
});
</script>
