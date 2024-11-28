<template>
    <router-view />
</template>

<script setup>
defineOptions({
    name: "App",
});

import { useQuasar } from "quasar";

const $q = useQuasar();
$q.iconMapFn = (iconName) => {
    if (iconName.startsWith("flaticon") === true) {
        return {
            cls: iconName,
        };
    }
};
</script>
