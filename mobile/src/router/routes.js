const routes = [
    {
        path: "/",
        component: () => import("layouts/MainLayout.vue"),
        children: [
            {
                name: "Discover",
                path: "",
                component: () => import("pages/DiscoverPage.vue"),
            },
            {
                name: "Home",
                path: "home",
                component: () => import("pages/HomePage.vue"),
            },
            {
                name: "BMS",
                path: "bms",
                component: () => import("pages/BMSPage.vue"),
            },
            {
                name: "PSU",
                path: "psu",
                component: () => import("pages/PSUPage.vue"),
            },
            {
                name: "MCU",
                path: "mcu",
                component: () => import("pages/MCUPage.vue"),
            },
            {
                name: "Inverter",
                path: "inverter",
                component: () => import("pages/InverterPage.vue"),
            },
        ],
    },

    // Always leave this as last one,
    // but you can also remove it
    {
        path: "/:catchAll(.*)*",
        component: () => import("pages/ErrorNotFound.vue"),
    },
];

export default routes;
