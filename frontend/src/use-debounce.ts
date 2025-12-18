import { watch, ref } from 'vue'

export function useDebounce<T>(value: T, delay: number) {
    const debouncedValue = ref<T>(value);
    let timeoutId: ReturnType<typeof setTimeout>;

    // Watch the value and debounce updates
    watch(
        () => value,
        (newVal) => {
            console.log('useDebounce newVal', newVal)
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                if (debouncedValue.value !== newVal) {
                debouncedValue.value = newVal;
                }
            }, delay);
        },
        { immediate: true }
    );

    // Clear timeout on unmount
    //   onBeforeUnmount(() => {
    //     clearTimeout(timeoutId);
    //   });
    console.log('debouncedValue', debouncedValue)
    return debouncedValue.value
}