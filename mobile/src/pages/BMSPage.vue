<template>
    <q-page class="">
        <highcharts :options="chartOptions"></highcharts>

        <div class="text-h5 q-mt-lg text-bold">{{ $t("bms") }}</div>
        <div class="q-mt-md error-message" v-for="error in errors" :key="error">
            {{ error }}
        </div>

        <div class="row q-mt-md">
            <div class="col-9"><span>■</span> {{ $t("batteryLevel") }}</div>
            <div class="col text-right" v-if="bmsStore.level">
                {{ bmsStore.level }}%
            </div>
            <div class="col text-right text-grey-5" v-if="!bmsStore.level">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9"><span>■</span> {{ $t("batteryVoltage") }}</div>
            <div class="col text-right" v-if="bmsStore.voltage">
                {{ bmsStore.voltage.toFixed(2) }} {{ $t("volt") }}
            </div>
            <div class="col text-right text-grey-5" v-if="!bmsStore.voltage">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9"><span>■</span> {{ $t("mcuConsumption") }}</div>
            <div class="col text-right" v-if="bmsStore.voltage">
                {{ bmsStore.mcu_consumption.toFixed(2) }} {{ $t("ah") }}
            </div>
            <div
                class="col text-right text-grey-5"
                v-if="!bmsStore.mcu_consumption"
            >
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: POWER_COLOR }">■</span>
                {{ $t("current") }}
            </div>
            <div class="col text-right">{{ bmsStore.current }}А</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: DC_COLOR }">■</span>
                {{ $t("cellVoltage") }} 1
            </div>
            <div class="col text-right" v-if="bmsStore.cell1Voltage">
                {{ bmsStore.cell1Voltage.toFixed(2) }}{{ $t("volt") }}
            </div>
            <div
                class="col text-right text-grey-5"
                v-if="!bmsStore.cell1Voltage"
            >
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: DC_COLOR }">■</span>
                {{ $t("cellVoltage") }} 2
            </div>
            <div class="col text-right" v-if="bmsStore.cell2Voltage">
                {{ bmsStore.cell2Voltage.toFixed(2) }}{{ $t("volt") }}
            </div>
            <div
                class="col text-right text-grey-5"
                v-if="!bmsStore.cell2Voltage"
            >
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: DC_COLOR }">■</span>
                {{ $t("cellVoltage") }} 3
            </div>
            <div class="col text-right" v-if="bmsStore.cell3Voltage">
                {{ bmsStore.cell3Voltage.toFixed(2) }}{{ $t("volt") }}
            </div>
            <div
                class="col text-right text-grey-5"
                v-if="!bmsStore.cell3Voltage"
            >
                NA
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: DC_COLOR }">■</span>
                {{ $t("cellVoltage") }} 4
            </div>
            <div class="col text-right" v-if="bmsStore.cell4Voltage">
                {{ bmsStore.cell4Voltage.toFixed(2) }}{{ $t("volt") }}
            </div>
            <div
                class="col text-right text-grey-5"
                v-if="!bmsStore.cell4Voltage"
            >
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: TEMPERATURE_COLOR }">■</span>
                {{ $t("mosTemperature") }}
            </div>
            <div class="col text-right">{{ bmsStore.mosTemperature }}℃</div>
        </div>
        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: TEMPERATURE_COLOR }">■</span>
                {{ $t("sensorTemperature") }} 1
            </div>
            <div class="col text-right" v-if="bmsStore.sensor1Temperature">
                {{ bmsStore.sensor1Temperature }} ℃
            </div>
            <div
                class="col text-right text-grey-5"
                v-if="!bmsStore.sensor1Temperature"
            >
                &mdash;
            </div>
        </div>
        <div class="row q-mt-md">
            <div class="col-9">
                <span :style="{ color: TEMPERATURE_COLOR }">■</span>
                {{ $t("sensorTemperature") }} 2
            </div>
            <div class="col text-right" v-if="bmsStore.sensor2Temperature">
                {{ bmsStore.sensor2Temperature }}℃
            </div>
            <div
                class="col text-right text-grey-5"
                v-if="!bmsStore.sensor2Temperature"
            >
                &mdash;
            </div>
        </div>
    </q-page>
</template>

<script setup>
import { computed, ref } from "vue";
import { useBMSStore } from "stores/bms";
import {
    HISTORY_BMS_CURRENT,
    HISTORY_BMS_CELL1_VOLTAGE,
    HISTORY_BMS_CELL2_VOLTAGE,
    HISTORY_BMS_CELL3_VOLTAGE,
    HISTORY_BMS_CELL4_VOLTAGE,
    TEMPERATURE_COLOR,
    DC_COLOR,
    POWER_COLOR,
} from "stores/uuids.js";
import { useI18n } from "vue-i18n";
const { t } = useI18n();
import { getErrors } from "src/utils/index.js";

const bmsStore = useBMSStore();

const errors = computed(() => {
    return getErrors(
        "bms",
        bmsStore.internalErrors ?? 0,
        bmsStore.externalErrors ?? 0,
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
        animation: false,
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
            min: -270,
            max: 350,
            title: { text: null },
            visible: true,
            tickPositions: [-250, -100, 0, 100, 250, 300],
            labels: {
                style: { color: POWER_COLOR, fontSize: "9px" },
                format: "{value}А",
                // align: "left",
                x: 25,
                y: 0,
            },
            gridLineWidth: 0,
            lineWidth: 0,
        },
        {
            opposite: true,
            title: { text: null },
            visible: true,
            min: 2.7,
            max: 3.7,
            tickPositions: [2.7, 3, 3.4, 3.7], // Positions for 3 labels
            labels: {
                style: { color: DC_COLOR, fontSize: "9px" },
                format: "{value}" + t("volt"),
                align: "left",
                x: -25,
                y: 0,
            },
            gridLineWidth: 0,
            lineWidth: 0, // Hide grid and axis lines
            plotLines: [
                {
                    value: 2.7, // Fixed Y-value
                    color: DC_COLOR, // Specific color
                    width: 1, // Line thickness
                    dashStyle: "dash", // Makes it dashed ('solid', 'dash', 'dot', etc.)
                },
                {
                    value: 3.5, // Fixed Y-value
                    color: DC_COLOR, // Specific color
                    width: 1, // Line thickness
                    dashStyle: "dash", // Makes it dashed ('solid', 'dash', 'dot', etc.)
                },
            ],
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
            animation: false,
            clip: false,
        },
    },
    series: [
        {
            data: bmsStore.chartData[HISTORY_BMS_CURRENT],
            lineWidth: 4,
            lineColor: POWER_COLOR,
            yAxis: 0,
        },
        {
            data: bmsStore.chartData[HISTORY_BMS_CELL1_VOLTAGE],
            lineWidth: 1,
            lineColor: DC_COLOR,
            yAxis: 1,
        },
        {
            data: bmsStore.chartData[HISTORY_BMS_CELL2_VOLTAGE],
            lineWidth: 1,
            lineColor: DC_COLOR,
            yAxis: 1,
        },
        {
            data: bmsStore.chartData[HISTORY_BMS_CELL3_VOLTAGE],
            lineWidth: 1,
            lineColor: DC_COLOR,
            yAxis: 1,
        },
        {
            data: bmsStore.chartData[HISTORY_BMS_CELL4_VOLTAGE],
            lineWidth: 1,
            lineColor: DC_COLOR,
            yAxis: 1,
        },
    ],
});
</script>
