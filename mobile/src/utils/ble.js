function unpack(value) {
    if (value === 0) return null;
    return value - 1;
}

function unpack_version(value) {
    const major = value & 128;
    const minor = value & 127;
    return major + "." + minor + ".0";
}

function unpack_bool(value) {
    if (value === 0) return null;
    if (value === 1) return false;
    if (value === 2) return true;
}

function pack_bool(value) {
    if (value === true) return 0x01;
    return 0x00;
}

function unpack_voltage(value) {
    if (value === null) return null;
    if (value === 0) return null;
    return (value - 1) / 100;
}

function unpack_current(value) {
    if (value === null) return null;
    if (value === 0) return null;

    value = value - 1;
    const direction = value & (1 << 15);
    const current = Math.round((value & (0xffff >> 1)) / 100);

    if (direction) return current;
    return -current;
}

function unpack_cell_voltage(value) {
    if (value === null) return null;
    if (value === 0) return null;
    return 2.5 + (value - 1) / 100;
}

function to_hex(value) {
    const bytes = new Uint8Array(
        value.buffer,
        value.byteOffset,
        value.byteLength,
    );
    return Array.from(bytes)
        .map((byte) => byte.toString(16).padStart(2, "0"))
        .join("");
}

export {
    unpack,
    unpack_bool,
    unpack_voltage,
    unpack_cell_voltage,
    unpack_current,
    unpack_version,
    pack_bool,
    to_hex,
};
