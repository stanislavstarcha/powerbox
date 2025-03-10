function dataViewToHexDump(dataview) {
    const bytes = [];
    for (let i = 0; i < dataview.byteLength; i++) {
        bytes.push(dataview.getUint8(i).toString(16).padStart(2, "0"));
    }
    return bytes.join(" ");
}

export { dataViewToHexDump };
