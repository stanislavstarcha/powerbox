<template>
    <q-page class="">
        <highcharts :options="chartOptions"></highcharts>
        <div class="text-h5 q-mt-lg text-bold">Блок живлення</div>
        <div v-if="psuStore.hasErrors()">
            <div v-for="error in errors" :key="error" class="error-message">
                {{ error }}
            </div>
        </div>
        <div class="row q-mt-md">
            <div class="col-10">Напруга</div>
            <div class="col-2" v-if="psuStore.voltage">
                {{ psuStore.voltage?.toFixed(2) }} В
            </div>
            <div class="col-2 text-grey-5" v-if="!psuStore.voltage">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">Температура</div>
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

const psuStore = usePSUStore();
const errors = computed(() => {
    if (!psuStore.internalErrors) return [];

    const results = [];

    if (psuStore.internalErrors & (1 << 0)) {
        results.push("err 1");
    }

    if (psuStore.internalErrors & (1 << 0)) {
        results.push("Системна помилка контролеру");
    }

    if (psuStore.internalErrors & (1 << 1)) {
        results.push("Неочикувана системна помилка");
    }

    if (psuStore.internalErrors & (1 << 2)) {
        results.push("Пристрій не відповідає");
    }

    if (psuStore.internalErrors & (1 << 3)) {
        results.push("Невалідна відповідь пристрія");
    }

    if (psuStore.internalErrors & (1 << 4)) {
        results.push("Помилка сенсору температури");
    }

    if (psuStore.internalErrors & (1 << 5)) {
        results.push("Помилка сенсору вольтметра");
    }

    if (psuStore.internalErrors & (1 << 6)) {
        results.push("pin initi");
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
            max: 15,
            tickPositions: [0, 12, 15], // Positions for 3 labels
            labels: {
                style: { fontSize: "9px" },
                format: "{value}В",
                align: "left", // Aligns labels to the right
                x: 5,
                y: 10,
            },
            gridLineWidth: 0,
            lineWidth: 0, // Hide grid and axis lines
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
            lineWidth: 4, // Minimal line thickness, adjust as needed
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
