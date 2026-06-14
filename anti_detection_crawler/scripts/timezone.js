// =============================================================
// 时区与语言伪装脚本
// 修改 Intl.DateTimeFormat().resolvedOptions().timeZone
// =============================================================

(function() {
    'use strict';

    const TIMEZONE_CONFIG = {
        timezone: 'Asia/Shanghai',
        timezoneOffset: -480
    };

    // 重写 Date.getTimezoneOffset
    const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
    Date.prototype.getTimezoneOffset = function() {
        return TIMEZONE_CONFIG.timezoneOffset;
    };

    // 重写 Intl.DateTimeFormat
    if (window.Intl && window.Intl.DateTimeFormat) {
        const OriginalDateTimeFormat = window.Intl.DateTimeFormat;
        window.Intl.DateTimeFormat = function(...args) {
            // 强制使用指定时区
            if (args.length === 0 || !args[0].timeZone) {
                args[0] = args[0] || {};
                args[0].timeZone = TIMEZONE_CONFIG.timezone;
            }
            return new OriginalDateTimeFormat(...args);
        };
        window.Intl.DateTimeFormat.prototype = OriginalDateTimeFormat.prototype;
        window.Intl.DateTimeFormat.supportedLocalesOf = OriginalDateTimeFormat.supportedLocalesOf;
    }

    // 重写 resolvedOptions
    if (window.Intl && window.Intl.DateTimeFormat && window.Intl.DateTimeFormat.prototype) {
        const originalResolvedOptions = window.Intl.DateTimeFormat.prototype.resolvedOptions;
        window.Intl.DateTimeFormat.prototype.resolvedOptions = function() {
            const options = originalResolvedOptions.call(this);
            options.timeZone = TIMEZONE_CONFIG.timezone;
            return options;
        };
    }

    console.log('[Anti-Detection] 时区伪装已启用: ' + TIMEZONE_CONFIG.timezone);
})();
