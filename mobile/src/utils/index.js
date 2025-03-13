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

export { dataViewToHexDump, formatTimeElapsed, getErrors };
