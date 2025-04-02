<template>
    <q-page class="hide-bottom-space">
        <div class="text-h5 q-mt-lg text-bold">{{ $t("debugPage") }}</div>
        <div class="row q-mt-md items-center">
            <q-btn size="xs" @click="disconnect()">{{
                $t("disconnect")
            }}</q-btn>
            <q-btn size="xs" @click="reboot()">{{ $t("reboot") }}</q-btn>
        </div>
        <div
            class="log-message q-mb-md"
            v-for="log in [...logsArray].reverse()"
            :key="log.timestamp"
            :style="{ color: log.color }"
        >
            [{{ log.level }}] [{{ log.timestamp }}] - {{ log.message }}
        </div>
    </q-page>
</template>

<script setup>
import { numbersToDataView } from "@capacitor-community/bluetooth-le";
import { computed, ref, onMounted } from "vue";
import { useAppStore } from "stores/app";
const appStore = useAppStore();

import {
    BLE_LOG_STATE_UUID,
    COMMAND_START_LOGS,
    COMMAND_STOP_LOGS,
} from "stores/uuids";

const LOG_LEVEL_INFO = 0;
const LOG_LEVEL_DEBUG = 1;

const disconnect = () => {
    appStore.disconnect();
};

const logsArray = ref([]);
const maxLogs = 1000;
let logBuffer = ""; // Stores partial message

const logLevels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"];
const logColors = {
    ERROR: "red",
    WARNING: "orange",
    INFO: "black",
    DEBUG: "blue",
};

const onLogMessage = (view) => {
    const byte = view.getInt8(0);
    const level = byte & 0b111; // Bits 0-2
    const format = (byte >> 3) & 0b111; // Bits 3-4

    const messageChunk = new TextDecoder().decode(
        new Uint8Array(view.buffer, view.byteOffset + 1, view.byteLength - 1),
    );

    if (format === 0) {
        logBuffer = messageChunk; // Start new message
    } else if (format === 1) {
        logBuffer += messageChunk; // Append to existing
    } else if (format === 2) {
        logBuffer += messageChunk; // Complete message

        const timestamp = new Date().toLocaleTimeString();
        const levelText = logLevels[level] || "UNKNOWN";
        const color = logColors[levelText] || "black";

        logsArray.value.push({
            level: levelText,
            timestamp,
            message: logBuffer,
            color,
        });

        if (logsArray.value.length > maxLogs) {
            logsArray.value.shift(); // Remove the oldest log entry
        }

        logBuffer = ""; // Reset buffer
    }
};

onMounted(async () => {
    await appStore.runBLECommand(numbersToDataView([COMMAND_START_LOGS]));
    appStore.subscribeToEvents(BLE_LOG_STATE_UUID, onLogMessage);
});
</script>
