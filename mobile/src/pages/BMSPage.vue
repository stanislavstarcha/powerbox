<template>
    <q-page class="">
        <highcharts :options="chartOptions"></highcharts>

        <div class="text-h5 q-mt-lg text-bold">{{ $t("bms") }}</div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("batteryLevel") }}</div>
            <div class="col" v-if="bmsStore.level">{{ bmsStore.level }}%</div>
            <div class="col-2 text-grey-5" v-if="!bmsStore.level">&mdash;</div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("batteryVoltage") }}</div>
            <div class="col-2" v-if="bmsStore.voltage">
                {{ bmsStore.voltage.toFixed(2) }} {{ $t("volt") }}
            </div>
            <div class="col-2 text-grey-5" v-if="!bmsStore.voltage">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("current") }}</div>
            <div class="col-2" v-if="bmsStore.current">
                {{ bmsStore.current }} А
            </div>
            <div class="col-2 text-grey-5" v-if="!bmsStore.current">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("cellVoltage") }} 1</div>
            <div class="col-2" v-if="bmsStore.cell1Voltage">
                {{ bmsStore.cell1Voltage.toFixed(2) }} {{ $t("volt") }}
            </div>
            <div class="col-2 text-grey-5" v-if="!bmsStore.cell1Voltage">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("cellVoltage") }} 2</div>
            <div class="col-2" v-if="bmsStore.cell2Voltage">
                {{ bmsStore.cell2Voltage.toFixed(2) }} {{ $t("volt") }}
            </div>
            <div class="col-2 text-grey-5" v-if="!bmsStore.cell2Voltage">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("cellVoltage") }} 3</div>
            <div class="col-2" v-if="bmsStore.cell3Voltage">
                {{ bmsStore.cell3Voltage.toFixed(2) }} {{ $t("volt") }}
            </div>
            <div class="col-2 text-grey-5" v-if="!bmsStore.cell3Voltage">
                NA
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("cellVoltage") }} 4</div>
            <div class="col-2" v-if="bmsStore.cell4Voltage">
                {{ bmsStore.cell4Voltage.toFixed(2) }} {{ $t("volt") }}
            </div>
            <div class="col-2 text-grey-5" v-if="!bmsStore.cell4Voltage">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("mosTemperature") }}</div>
            <div class="col-2">{{ bmsStore.mosTemperature }} ℃</div>
        </div>
        <div class="row q-mt-md">
            <div class="col-10">{{ $t("sensorTemperature") }} 1</div>
            <div class="col-2" v-if="bmsStore.sensor1Temperature">
                {{ bmsStore.sensor1Temperature }} ℃
            </div>
            <div class="col-2 text-grey-5" v-if="!bmsStore.sensor1Temperature">
                &mdash;
            </div>
        </div>
        <div class="row q-mt-md">
            <div class="col-10">{{ $t("sensorTemperature") }} 2</div>
            <div class="col-2" v-if="bmsStore.sensor2Temperature">
                {{ bmsStore.sensor2Temperature }} ℃
            </div>
            <div class="col-2 text-grey-5" v-if="!bmsStore.sensor2Temperature">
                &mdash;
            </div>
        </div>

        <div class="row q-mt-md">
            <div class="col-10">{{ $t("allowCharging") }}</div>
            <div class="col-2">
                <q-toggle
                    v-model="bmsStore.allowCharging"
                    color="grey"
                    disable
                />
            </div>
        </div>
        <div class="row q-mt-md">
            <div class="col-10">{{ $t("allowDischarging") }}</div>
            <div class="col-2">
                <q-toggle
                    v-model="bmsStore.allowDischarging"
                    color="grey"
                    disable
                />
            </div>
        </div>
    </q-page>
</template>

<script setup>
import { ref } from "vue";
import { useBMSStore } from "stores/bms";
import {
    HISTORY_BMS_CURRENT,
    HISTORY_BMS_CELL1_VOLTAGE,
    HISTORY_BMS_CELL2_VOLTAGE,
    HISTORY_BMS_CELL3_VOLTAGE,
    HISTORY_BMS_CELL4_VOLTAGE,
} from "stores/uuids.js";
import { useI18n } from "vue-i18n";

const bmsStore = useBMSStore();
const { t } = useI18n();

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
            min: -250,
            max: 250,
            title: { text: null },
            visible: true,
            tickPositions: [-250, -100, 0, 100, 250],
            labels: {
                style: { fontSize: "9px" },
                format: "{value}А",
                align: "left",
                x: 5,
                y: 10,
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
            tickPositions: [2.7, 3, 3.6], // Positions for 3 labels
            labels: {
                style: { fontSize: "9px" },
                format: "{value}" + t("volt"),
                align: "left",
                x: -25,
                y: 10,
            },
            gridLineWidth: 0,
            lineWidth: 0, // Hide grid and axis lines
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
            lineColor: "red",
            yAxis: 0,
        },
        {
            data: bmsStore.chartData[HISTORY_BMS_CELL1_VOLTAGE],
            lineWidth: 1,
            lineColor: "green",
            yAxis: 1,
        },
        {
            data: bmsStore.chartData[HISTORY_BMS_CELL2_VOLTAGE],
            lineWidth: 1,
            lineColor: "green",
            yAxis: 1,
        },
        {
            data: bmsStore.chartData[HISTORY_BMS_CELL3_VOLTAGE],
            lineWidth: 1,
            lineColor: "green",
            yAxis: 1,
        },
        {
            data: bmsStore.chartData[HISTORY_BMS_CELL4_VOLTAGE],
            lineWidth: 1,
            lineColor: "green",
            yAxis: 1,
        },
    ],
});
</script>
