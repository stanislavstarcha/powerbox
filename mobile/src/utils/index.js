import { numbersToDataView } from "@capacitor-community/bluetooth-le";

import { COMMAND_CONF_SET_KEY } from "stores/uuids.js";

function dataViewToHexDump(dataview) {
    const bytes = [];
    for (let i = 0; i < dataview.byteLength; i++) {
        bytes.push(dataview.getUint8(i).toString(16).padStart(2, "0"));
    }
    return bytes.join(" ");
}

function formatTimeElapsed(seconds) {
    const units = [
        { label: "d", value: 86400 },
        { label: "h", value: 3600 },
        { label: "m", value: 60 },
        { label: "s", value: 1 },
    ];

    let result = [];
    for (let { label, value } of units) {
        let amount = Math.floor(seconds / value);
        if (amount > 0) {
            result.push(`${amount}${label}`);
            seconds %= value;
        }
    }
    return result.join(" ") || "0s";
}

function getErrors(device, internal, external, t) {
    const errors = [];

    for (let bit = 0; bit < 8; bit += 1) {
        if (internal & (1 << bit)) {
            errors.push(t(device + "InternalError" + bit));
        }
    }

    for (let bit = 0; bit < 8; bit += 1) {
        if (external & (1 << bit)) {
            errors.push(t(device + "ExternalError" + bit));
        }
    }

    return errors;
}

function pack_bool_param(param, value) {
    return numbersToDataView([
        COMMAND_CONF_SET_KEY,
        param,
        value ? 0x01 : 0x00,
    ]);
}

function pack_int_param(param, value) {
    return numbersToDataView([
        COMMAND_CONF_SET_KEY,
        param,
        value ? 0x01 : 0x00,
    ]);
}

function pack_float_param(param, value) {
    const view = new DataView(new ArrayBuffer(6));
    view.setInt8(0, COMMAND_CONF_SET_KEY);
    view.setInt8(1, param);
    view.setFloat32(2, value, true);
    return view;
}

function pack_string_param(param, value) {
    const encoded = new TextEncoder().encode(value);
    const buffer = new ArrayBuffer(encoded.length + 2);
    const view = new DataView(buffer);

    view.setInt8(0, COMMAND_CONF_SET_KEY);
    view.setInt8(1, param);

    for (let i = 0; i < encoded.length; i++) {
        view.setUint8(i + 2, encoded[i]);
    }

    return view;
}

export {
    dataViewToHexDump,
    formatTimeElapsed,
    getErrors,
    pack_bool_param,
    pack_float_param,
    pack_int_param,
    pack_string_param,
};
