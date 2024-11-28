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
                Потужність
            </div>
            <div class="col-auto q-ml-xs q-mr-lg">
                {{ inverterStore.power }} Вт
            </div>
            <div class="col-auto text-caption text-grey-7 q-ml-xs">Напруга</div>
            <div class="col-auto q-ml-xs q-mr-lg">{{ bmsStore.voltage }} В</div>
        </div>

        <highcharts :options="chartOptions" class="q-mt-md"></highcharts>

        <div class="row q-mt-md">
            <div class="col-6 text-center">
                <div class="text-h5 text-weight-bold">Заряд</div>
                <div class="text-caption text-grey-5">
                    Натисніть щоб почати заряджати батарею
                </div>
                <q-toggle
                    :color="charging ? 'red' : 'grey'"
                    v-model="charging"
                    size="70px"
                />

                <div class="text-caption text-grey-5">
                    Максимальний струм заряду.
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
                <div class="text-h5 text-weight-bold">Інвертор</div>
                <div class="text-caption text-grey-5">
                    Натисніть для генерації 220В
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

const bmsStore = useBMSStore();
const psuStore = usePSUStore();
const inverterStore = useInverterStore();

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
        spacing: [0, 0, 0, 0], // Removes outer spacing around the chart
        margin: [10, 0, 10, 0], // Removes margins within the chart area
        height: 100,
        animation: false,
    },
    title: {
        text: null, // Hides title
    },
    xAxis: {
        visible: false, // Hides the x-axis completely
    },
    yAxis: {
        max: 105,
        title: { text: null },
        visible: true, // Hides the x-axis completely
        tickPositions: [0, 50, 100], // Positions for 3 labels
        labels: {
            style: { fontSize: "9px" },
            format: "{value}%",
            align: "left", // Aligns labels to the right
            x: 5, // Adjust to overlap within the chart area
            y: 10, // Fine-tune vertical position if needed
        },
        gridLineWidth: 0,
        lineWidth: 0, // Hide grid and axis lines
    },
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
            animation: false,
            clip: false,
            lineWidth: 4, // Minimal line thickness, adjust as needed
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
