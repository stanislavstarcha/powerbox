import { acceptHMRUpdate, defineStore } from "pinia";
import {
    unpack,
    unpack_bool,
    unpack_voltage,
    unpack_cell_voltage,
    unpack_current,
} from "src/utils/ble.js";

import { dataViewToHexDump } from "src/utils";

import {
    HISTORY_BMS_SOC,
    HISTORY_BMS_CURRENT,
    HISTORY_BMS_CELL1_VOLTAGE,
    HISTORY_BMS_CELL2_VOLTAGE,
    HISTORY_BMS_CELL3_VOLTAGE,
    HISTORY_BMS_CELL4_VOLTAGE,
} from "stores/uuids";

export const useBMSStore = defineStore("bms", {
    state: () => ({
        level: null,
        voltage: null,
        current: null,
        allowCharging: null,
        allowDischarging: null,
        mosTemperature: null,
        sensor1Temperature: null,
        sensor2Temperature: null,
        cell1Voltage: null,
        cell2Voltage: null,
        cell3Voltage: null,
        cell4Voltage: null,
        internalErrors: null,
        externalErrors: null,
        chartData: {},
        chartMappings: {
            [HISTORY_BMS_SOC]: unpack,
            [HISTORY_BMS_CURRENT]: unpack_current,
            [HISTORY_BMS_CELL1_VOLTAGE]: unpack_cell_voltage,
            [HISTORY_BMS_CELL2_VOLTAGE]: unpack_cell_voltage,
            [HISTORY_BMS_CELL3_VOLTAGE]: unpack_cell_voltage,
            [HISTORY_BMS_CELL4_VOLTAGE]: unpack_cell_voltage,
        },
    }),

    actions: {
        parseState(view) {
            let offset = 0;
            console.log("BMS state", dataViewToHexDump(view));

            // voltage
            this.voltage = unpack_voltage(view.getUint16(offset));
            offset += 2;

            // current
            this.current = unpack_current(view.getUint16(offset));
            offset += 2;

            // level
            this.level = unpack(view.getUint8(offset));
            offset += 1;

            // charging allowed
            this.allowCharging = unpack_bool(view.getUint8(offset));
            offset += 1;

            // discharging allowed
            this.allowDischarging = unpack_bool(view.getUint8(offset));
            offset += 1;

            // mos temp
            this.mosTemperature = unpack(view.getUint8(offset));
            offset += 1;

            // sensor 1 temp
            this.sensor1Temperature = unpack(view.getUint8(offset));
            offset += 1;

            // sensor 2 temp
            this.sensor2Temperature = unpack(view.getUint8(offset));
            offset += 1;

            // cell 1 voltage
            this.cell1Voltage = unpack_cell_voltage(view.getUint8(offset));
            offset += 1;

            // cell 2 voltage
            this.cell2Voltage = unpack_cell_voltage(view.getUint8(offset));
            offset += 1;

            // cell 3 voltage
            this.cell3Voltage = unpack_cell_voltage(view.getUint8(offset));
            offset += 1;

            // cell 4 voltage
            this.cell4Voltage = unpack_cell_voltage(view.getUint8(offset));
            offset += 1;

            this.externalErrors = unpack(view.getUint16(offset));
            offset += 2;

            this.internalErrors = unpack(view.getUint8(offset));
            offset += 1;
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useBMSStore, import.meta.hot));
}
