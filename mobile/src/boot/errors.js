import { boot } from "quasar/wrappers";

export default boot(({ app }) => {
    app.config.errorHandler = (e, vm, info) => {
        console.error("Unhandled Error:", e.message, info);
    };

    window.addEventListener("error", function (e) {
        console.error("Unhandled Exception:", e.reason.message);
        return false;
    });

    window.addEventListener("unhandledrejection", function (e) {
        console.error("Unhandled Exception:", e.reason.message);
    });
});
