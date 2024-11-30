import {
    bmsUUID,
    psuUUID,
    espUUID,
    inverterUUID,
    historyUUID,
    setChargingUUID,
    setDischargingUUID,
    setCurrentUUID,
    HISTORY_BMS_SOC,
} from "stores/uuids";

const randomValue = (max = 100, min = 0) =>
    Math.floor(Math.random() * (max - min + 1)) + min;

const genBmsState = () => {
    let offset = 0;
    const buffer = new ArrayBuffer(18);
    const view = new DataView(buffer);

    // level
    view.setUint8(offset, randomValue(100));
    offset += 1;

    // voltage
    view.setUint8(offset, randomValue(150));
    offset += 1;

    // current
    view.setUint16(offset, randomValue(512));
    offset += 2;

    // mos temp
    view.setUint8(offset, randomValue(75));
    offset += 1;

    // sensor 1 temp
    view.setUint8(offset, randomValue(75));
    offset += 1;

    // sensor 2 temp
    view.setUint8(offset, randomValue(75));
    offset += 1;

    // cell 1 voltage
    view.setUint8(offset, randomValue(100));
    offset += 1;

    // cell 2 voltage
    view.setUint8(offset, randomValue(100));
    offset += 1;

    // cell 3 voltage
    view.setUint8(offset, randomValue(100));
    offset += 1;

    // cell 4 voltage
    view.setUint8(offset, randomValue(100));
    offset += 1;

    // cell 1 resistance
    view.setUint8(offset, randomValue(255));
    offset += 1;

    // cell 2 resistance
    view.setUint8(offset, randomValue(255));
    offset += 1;

    // cell 3 resistance
    view.setUint8(offset, randomValue(255));
    offset += 1;

    // cell 4 resistance
    view.setUint8(offset, randomValue(255));
    offset += 1;

    // charging
    view.setUint8(offset, randomValue(1));
    offset += 1;

    // discharging
    view.setUint8(offset, randomValue(1));
    offset += 1;

    // balancing
    view.setUint8(offset, randomValue(1));
    offset += 1;

    // device error
    view.setUint8(offset, randomValue(1));
    offset += 1;

    // error
    view.setUint8(offset, randomValue(1));

    return buffer;
};

const genPsuState = () => {
    let offset = 0;
    const buffer = new ArrayBuffer(3);
    const view = new DataView(buffer);

    // voltage
    view.setUint16(offset, randomValue(1460));
    offset += 2;

    // temperature
    view.setUint8(offset, randomValue(150));
    offset += 1;

    // error
    view.setUint8(offset, randomValue(2));

    return buffer;
};

const genEspState = () => {
    let offset = 0;
    const buffer = new ArrayBuffer(9);
    const view = new DataView(buffer);

    // version
    view.setUint16(offset, randomValue(65535));
    offset += 2;

    // uptime
    view.setUint32(offset, randomValue(100000));
    offset += 4;

    // temperature
    view.setUint8(offset, randomValue(100));
    offset += 1;

    // memory
    view.setUint8(offset, randomValue(100));
    offset += 1;

    // error
    view.setUint8(offset, randomValue(2));

    return buffer;
};

const genInverterState = () => {
    let offset = 0;
    const buffer = new ArrayBuffer(6);
    const view = new DataView(buffer);

    // ac
    view.setUint8(offset, randomValue(255));
    offset += 1;

    // power
    view.setUint16(offset, randomValue(2500));
    offset += 2;

    // temperature
    view.setUint8(offset, randomValue(100));
    offset += 1;

    // error
    view.setUint8(offset, randomValue(1));
    offset += 1;

    // device error
    view.setUint8(offset, randomValue(1));

    return buffer;
};

const genHistoryIncrement = () => {
    return genHistoryState(HISTORY_BMS_SOC, 0, 16, 1, 0, 0, 100);
};

const onChargingControl = (value) => {
    modifiers[setDischargingUUID].callback(!value);
};
const onDischargingControl = (value) => {
    modifiers[setChargingUUID].callback(!value);
};

const onHistoryControl = (value) => {
    // generate bms level history
    if (value === 0) {
        modifiers[historyUUID].callback(
            genHistoryState(HISTORY_BMS_SOC, 0, 16, 0, 0, 0, 100),
        );
        modifiers[historyUUID].callback(
            genHistoryState(HISTORY_BMS_SOC, 64, 16, 0, 0, 0, 100),
        );

        modifiers[historyUUID].callback(
            genHistoryState(HISTORY_BMS_SOC, 100, 2, 0, 0, 0, 100),
        );
    }
};

const genHistoryState = (
    chartType,
    offset,
    length,
    incremental,
    dataType,
    min,
    max,
) => {
    const header = packHistoryHeader(
        chartType,
        0,
        0,
        incremental,
        dataType,
        length,
        offset,
    );
    const view = new DataView(new ArrayBuffer(4 + length * (dataType + 1)));
    view.setUint32(0, header);

    for (let i = 0; i < length; i++) {
        if (dataType === 0) {
            view.setUint8(4 + i, randomValue(max, min));
        }
    }

    return view;
};

const packHistoryHeader = (
    chartType,
    resolution,
    snapshot,
    incremental,
    dataType,
    length,
    offset,
) => {
    // Ensure each value fits within its assigned bit size
    chartType &= 0b11111; // 5 bits
    resolution &= 0b1; // 1 bit
    snapshot &= 0b1; // 1 bit
    incremental &= 0b1; // 1 bit
    dataType &= 0b1; // 1 bit
    length &= 0b11111; // 5 bits
    offset &= 0xff; // 8 bits (0xFF is hexadecimal for 255, which is 8 bits)

    // Pack each field into a 32-bit integer
    return (
        (chartType << 27) |
        (resolution << 26) |
        (snapshot << 25) |
        (incremental << 24) |
        (dataType << 23) |
        (length << 18) |
        offset
    );
};

const generators = {
    [bmsUUID]: genBmsState,
    [psuUUID]: genPsuState,
    [espUUID]: genEspState,
    [inverterUUID]: genInverterState,
    [historyUUID]: genHistoryIncrement,
};

const fixed = {
    [setChargingUUID]: true,
    [setDischargingUUID]: false,
    [setCurrentUUID]: 2,
};

const modifiers = {
    [setChargingUUID]: {
        modifier: onChargingControl,
        callback: null,
    },
    [setDischargingUUID]: {
        modifier: onDischargingControl,
        callback: null,
    },

    [historyUUID]: {
        modifier: onHistoryControl,
        callback: null,
    },
};

function requestLEScan(options, callback) {
    console.debug("Request BLE scan");
    callback({
        device: {
            deviceId: "d1",
            name: "Dobrotvir",
        },
    });

    callback({
        device: {
            deviceId: "d2",
            name: "Dobrotvir",
        },
    });
}

async function initialize() {
    console.debug("Initializing BLE");
}

async function stopLEScan() {
    console.debug("Stopping BLE scan");
}

async function connect(deviceId) {
    console.debug("Connecting to device", deviceId);
}

async function read(deviceId, serviceUUID, characteristicUUID) {
    if (characteristicUUID in generators) {
        return generators[characteristicUUID]();
    }

    if (characteristicUUID in fixed) {
        return fixed[characteristicUUID];
    }
}

async function write(deviceId, serviceUUID, characteristicUUID, data) {
    const value = new Uint8Array(data.buffer);
    if (characteristicUUID in modifiers) {
        modifiers[characteristicUUID].modifier(data);
    }
}

async function startNotifications(
    deviceId,
    serviceUUID,
    characteristicUUID,
    callback,
) {
    if (characteristicUUID in generators) {
        const genFunction = generators[characteristicUUID];
        setInterval(() => callback(genFunction()), 5000);
    }

    if (characteristicUUID in modifiers) {
        modifiers[characteristicUUID].callback = callback;
    }
}

export {
    initialize,
    connect,
    requestLEScan,
    read,
    write,
    startNotifications,
    stopLEScan,
};
