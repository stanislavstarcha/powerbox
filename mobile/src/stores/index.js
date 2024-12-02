import { store } from "quasar/wrappers";
import { createPinia } from "pinia";
import _ from "lodash";

import { HISTORY_LENGTH } from "stores/uuids";

/*
 * If not building with SSR mode, you can
 * directly export the Store instantiation;
 *
 * The function below can be async too; either use
 * async/await or return a Promise which resolves
 * with the Store instance.
 */

function DeviceStorePlugin({ app, options, store }) {
    store.hasErrors = () => {
        const internal = _.isNull(store.$state.internalErrors)
            ? 0
            : store.$state.internalErrors;
        const external = _.isNull(store.$state.externalErrors)
            ? 0
            : store.$state.externalErrors;
        return internal + external;
    };

    store.initialiseChartData = () => {
        store.$state.chartData = _.mapValues(store.$state.chartMappings, () =>
            new Array(HISTORY_LENGTH).fill(null),
        );
    };

    store.adjustChartData = (chartType, data) => {
        const callback = store.$state.chartMappings[chartType];
        if (_.isNull(callback)) return data;
        return _.map(data, (x) => callback(x));
    };

    store.patchChartData = (chartType, offset, data) => {
        store.$state.chartData[chartType].splice(
            offset,
            data.length,
            ...store.adjustChartData(chartType, data),
        );
    };

    store.pushChartData = (chartType, offset, data) => {
        store.$state.chartData[chartType].push(
            ...store.adjustChartData(chartType, data),
        );
        store.$state.chartData[chartType].splice(0, data.length);
    };
}

export default store((/* { ssrContext } */) => {
    const pinia = createPinia();

    // You can add Pinia plugins here
    pinia.use(DeviceStorePlugin);

    return pinia;
});
