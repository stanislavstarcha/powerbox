import _ from "lodash";

import { acceptHMRUpdate, defineStore } from "pinia";

import { useBMSStore } from "stores/bms";
import { usePSUStore } from "stores/psu";
import { useInverterStore } from "stores/inverter";

import {
    HISTORY_BMS_SOC,
    HISTORY_BMS_CURRENT,
    HISTORY_BMS_CELL1_VOLTAGE,
    HISTORY_BMS_CELL2_VOLTAGE,
    HISTORY_BMS_CELL3_VOLTAGE,
    HISTORY_BMS_CELL4_VOLTAGE,
    HISTORY_INVERTER_POWER,
    HISTORY_INVERTER_TEMPERATURE,
    HISTORY_INVERTER_RPM,
    HISTORY_PSU_RPM,
    HISTORY_PSU_TEMPERATURE_1,
    HISTORY_PSU_TEMPERATURE_2,
    HISTORY_PSU_POWER_1,
    HISTORY_PSU_POWER_2,
} from "stores/uuids";

export const useHistoryStore = defineStore("history", {
    state: () => ({
        routes: null,
    }),

    actions: {
        initialise() {
            const bmsStore = useBMSStore();
            const psuStore = usePSUStore();
            const inverterStore = useInverterStore();

            this.routes = {
                [HISTORY_BMS_SOC]: bmsStore,
                [HISTORY_BMS_CURRENT]: bmsStore,
                [HISTORY_BMS_CELL1_VOLTAGE]: bmsStore,
                [HISTORY_BMS_CELL2_VOLTAGE]: bmsStore,
                [HISTORY_BMS_CELL3_VOLTAGE]: bmsStore,
                [HISTORY_BMS_CELL4_VOLTAGE]: bmsStore,
                [HISTORY_PSU_TEMPERATURE_1]: psuStore,
                [HISTORY_PSU_TEMPERATURE_2]: psuStore,
                [HISTORY_PSU_POWER_1]: psuStore,
                [HISTORY_PSU_POWER_2]: psuStore,
                [HISTORY_PSU_RPM]: psuStore,
                [HISTORY_INVERTER_POWER]: inverterStore,
                [HISTORY_INVERTER_TEMPERATURE]: inverterStore,
                [HISTORY_INVERTER_RPM]: inverterStore,
            };
        },

        parseState(view) {
            const { chartType, incremental, dataType, length, offset } =
                this.unpackHeader(view.getUint32(0, true));

            const values = this.parseHistoricalData(view, dataType, length);

            if (_.has(this.routes, chartType)) {
                if (incremental === 1) {
                    console.log(
                        "Pushing chart data",
                        chartType,
                        offset,
                        values,
                    );
                    this.routes[chartType].pushChartData(
                        chartType,
                        offset,
                        values,
                    );
                } else {
                    console.log(
                        "Patching chart data",
                        chartType,
                        offset,
                        values,
                    );
                    this.routes[chartType].patchChartData(
                        chartType,
                        offset,
                        values,
                    );
                }
            }
        },

        unpackHeader(packedValue) {
            // Extract each field by shifting and masking
            return {
                length: packedValue & 0xff, // 8 bits
                offset: (packedValue >> 8) & 0xff, // 8 bits
                incremental: (packedValue >> 16) & 0b1, // 1 bit
                dataType: (packedValue >> 17) & 0b1, // 1 bit
                chartType: (packedValue >> 18) & 0b111111, // 6 bits
            };
        },

        parseHistoricalData(dataView, dataType, numElements) {
            const values = [];

            // skip header
            let index = 4;

            for (let i = 0; i < numElements; i++) {
                if (dataType === 0) {
                    values.push(dataView.getUint8(index)); // Read one byte for uint8
                    index += 1;
                } else if (dataType === 1) {
                    values.push(dataView.getUint16(index, true)); // Read two bytes for uint16 (little-endian)
                    index += 2;
                } else {
                    throw new Error(`Unsupported type: ${type}`);
                }
            }
            return values;
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useHistoryStore, import.meta.hot));
}
