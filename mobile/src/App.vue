<template>
    <router-view />
</template>

<script setup>
import { onMounted } from "vue";
import { useQuasar } from "quasar";

defineOptions({
    name: "App",
});

onMounted(async () => {
    // console.log("App mounted");
    // const appStore = useAppStore();
    // await appStore.loadLanguage();
});

const $q = useQuasar();
$q.iconMapFn = (iconName) => {
    if (iconName.startsWith("flaticon") === true) {
        return {
            cls: iconName,
        };
    }
};
</script>
