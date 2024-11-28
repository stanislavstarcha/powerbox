import { numberToUUID } from "@capacitor-community/bluetooth-le";

const coreServiceUUID = numberToUUID(0x180f);
const bmsUUID = "549fa451-cf65-4ea1-a462-9527d8d06440";
const psuUUID = "bd9e30e5-3e45-4660-8a1f-2a4f12bfaa5e";
const espUUID = "a61dc670-fb5c-4f8c-afa8-7bcd088dc146";
const inverterUUID = "226396fe-22a8-48ce-aa95-188899618fd9";

const historyUUID = "b1e71c63-5154-4bc5-bad6-4dc170b926d4";
const commandUUID = "eb47891b-c111-463b-8f39-4a5115c352bd";

const chargingUUID = "3719b9de-d6ff-4170-bdb0-b9e7ade6a56e";
const dischargingUUID = "ed071461-02ae-4c54-a4d9-944cfd46b19d";
const currentUUID = "945fb6ac-a80a-4c9d-af17-36e83521e2ce";

const HISTORY_LENGTH = 180;

const HISTORY_BMS_SOC = 0;
const HISTORY_BMS_CURRENT = 1;
const HISTORY_BMS_CELL1_VOLTAGE = 2;
const HISTORY_BMS_CELL2_VOLTAGE = 3;
const HISTORY_BMS_CELL3_VOLTAGE = 4;
const HISTORY_BMS_CELL4_VOLTAGE = 5;
const HISTORY_PSU_VOLTAGE = 10;
const HISTORY_PSU_TEMPERATURE = 11;

const HISTORY_INVERTER_POWER = 20;
const HISTORY_INVERTER_TEMPERATURE = 21;

const DATA_TYPE_BYTE = 0;
const DATA_TYPE_WORD = 1;

export {
    coreServiceUUID,
    bmsUUID,
    psuUUID,
    espUUID,
    inverterUUID,
    historyUUID,
    commandUUID,
    chargingUUID,
    dischargingUUID,
    currentUUID,
    HISTORY_LENGTH,
    HISTORY_BMS_SOC,
    HISTORY_BMS_CURRENT,
    HISTORY_BMS_CELL1_VOLTAGE,
    HISTORY_BMS_CELL2_VOLTAGE,
    HISTORY_BMS_CELL3_VOLTAGE,
    HISTORY_BMS_CELL4_VOLTAGE,
    HISTORY_PSU_VOLTAGE,
    HISTORY_PSU_TEMPERATURE,
    HISTORY_INVERTER_POWER,
    HISTORY_INVERTER_TEMPERATURE,
    DATA_TYPE_BYTE,
    DATA_TYPE_WORD,
};
