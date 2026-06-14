// =============================================================
// Navigator 属性伪装脚本
// 修改 navigator.webdriver、navigator.plugins、navigator.languages
// 修复 Permissions、Chrome 特有属性等
// =============================================================

(function() {
    'use strict';

    // 1. 隐藏 webdriver 标志
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
        configurable: true
    });

    // 2. 修复 navigator.plugins
    const fakePlugins = [
        { name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
        { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
        { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
        { name: 'Microsoft Edge PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
        { name: 'WebKit built-in PDF', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }
    ];

    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const pluginsObj = fakePlugins.map(p => ({
                name: p.name,
                filename: p.filename,
                description: p.description,
                length: 1,
                item: function() { return this; },
                namedItem: function() { return this; }
            }));
            pluginsObj.length = fakePlugins.length;
            return pluginsObj;
        },
        configurable: true
    });

    // 3. 修复 navigator.languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en'],
        configurable: true
    });

    // 4. 修复 navigator.platform
    Object.defineProperty(navigator, 'platform', {
        get: () => 'Win32',
        configurable: true
    });

    // 5. 修复 navigator.hardwareConcurrency
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8,
        configurable: true
    });

    // 6. 修复 navigator.deviceMemory
    if (navigator.deviceMemory === undefined) {
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
            configurable: true
        });
    }

    // 7. 修复 Permissions API
    const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
    if (originalQuery) {
        window.navigator.permissions.query = function(parameters) {
            if (parameters.name === 'notifications') {
                return Promise.resolve({ state: Notification.permission });
            }
            return originalQuery.call(this, parameters);
        };
    }

    // 8. 修复 Chrome 特有对象
    if (!window.chrome) {
        window.chrome = {};
    }
    window.chrome.runtime = window.chrome.runtime || {};
    window.chrome.loadTimes = window.chrome.loadTimes || function() {};
    window.chrome.csi = window.chrome.csi || function() {};
    window.chrome.app = window.chrome.app || { isInstalled: false, InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }, RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' } };

    // 9. 修复 connection
    if (!navigator.connection) {
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                effectiveType: '4g',
                rtt: 50,
                downlink: 10,
                saveData: false
            }),
            configurable: true
        });
    }

    // 10. 隐藏 CDP 痕迹
    // 删除 cdc_开头的变量
    for (const key in document) {
        if (key.startsWith('cdc_') || key.startsWith('__$')) {
            try {
                delete document[key];
            } catch (e) {}
        }
    }

    // 11. 修复 notification.permission
    if (window.Notification && Notification.permission === 'denied') {
        Object.defineProperty(Notification, 'permission', {
            get: () => 'default',
            configurable: true
        });
    }

    console.log('[Anti-Detection] Navigator 指纹伪装已启用');
})();
